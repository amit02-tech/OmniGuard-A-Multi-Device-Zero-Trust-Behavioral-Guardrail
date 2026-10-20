import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from torch.utils.data import Dataset, DataLoader, random_split
import os

# --- 1. HARDWARE ACCELERATION ASSERTION ---
if not torch.cuda.is_available():
    raise SystemError("CUDA GPU is not detected. Please install the CUDA-enabled PyTorch build.")

device = torch.device("cuda")
print(f"[*] Engine Active on GPU: {torch.cuda.get_device_name(0)}")

# --- 2. VECTORIZATION & DATASET PIPELINE ---
VALID_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_\\/.:\"'^%$#@!&*"
CHAR_TO_INDEX = {char: idx + 1 for idx, char in enumerate(VALID_CHARS)}
VOCAB_SIZE = len(VALID_CHARS) + 1
MAX_SEQ_LENGTH = 128


def vectorize_command(cmd):
    cmd_str = str(cmd)
    vec = [CHAR_TO_INDEX.get(c, 0) for c in cmd_str[:MAX_SEQ_LENGTH]]
    vec += [0] * (MAX_SEQ_LENGTH - len(vec))
    return vec


class CommandDataset(Dataset):
    def __init__(self, csv_file):
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"Cannot find '{csv_file}'. Run dataset_builder.py first.")

        df = pd.read_csv(csv_file)
        # Drop duplicates across text commands to prevent data leakage
        df = df.drop_duplicates(subset=['Command']).dropna(subset=['Command', 'Label'])
        print(f"[*] Loaded {len(df)} unique commands from '{csv_file}'.")

        self.commands = [vectorize_command(cmd) for cmd in df['Command']]
        self.labels = df['Label'].astype(float).tolist()

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return (
            torch.tensor(self.commands[idx], dtype=torch.long),
            torch.tensor(self.labels[idx], dtype=torch.float32)
        )


# --- 3. HARDENED NEURAL NETWORK ARCHITECTURE ---
class EDRCommandClassifier(nn.Module):
    def __init__(self):
        super(EDRCommandClassifier, self).__init__()
        # Dense character embedding
        self.embedding = nn.Embedding(num_embeddings=VOCAB_SIZE, embedding_dim=64)

        # Conv Block 1: Scans character n-grams (kernel 5)
        self.conv1 = nn.Conv1d(in_channels=64, out_channels=128, kernel_size=5, padding=2)
        self.bn1 = nn.BatchNorm1d(128)
        self.relu = nn.ReLU()
        self.pool1 = nn.MaxPool1d(kernel_size=2)

        # Conv Block 2: Detects multi-character obfuscation patterns (kernel 3)
        self.conv2 = nn.Conv1d(in_channels=128, out_channels=128, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(128)
        self.pool2 = nn.MaxPool1d(kernel_size=2)

        # Regularization: Break co-adaptation of neurons
        self.dropout = nn.Dropout(0.3)

        # Classifier
        flattened_dim = 128 * (MAX_SEQ_LENGTH // 4)
        self.fc1 = nn.Linear(flattened_dim, 64)
        self.fc2 = nn.Linear(64, 1)  # Raw logits for BCEWithLogitsLoss

    def forward(self, x):
        x = self.embedding(x)
        x = x.permute(0, 2, 1)  # (batch, channels, seq_len)

        x = self.pool1(self.relu(self.bn1(self.conv1(x))))
        x = self.pool2(self.relu(self.bn2(self.conv2(x))))

        x = x.view(x.size(0), -1)
        x = self.dropout(x)
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        return self.fc2(x)


# --- 4. PRODUCTION TRAINING & VALIDATION LOOP ---
def train_production_model():
    dataset = CommandDataset('mitre_commands.csv')

    # 80% Training, 20% Unseen Validation
    val_size = int(0.2 * len(dataset))
    train_size = len(dataset) - val_size
    train_data, val_data = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_data, batch_size=64, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_data, batch_size=64, shuffle=False, pin_memory=True)

    model = EDRCommandClassifier().to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)

    best_val_loss = float('inf')
    epochs = 10

    print(f"\n[*] Commencing Enterprise Training ({train_size} train, {val_size} validation)...")
    print("-" * 75)

    for epoch in range(1, epochs + 1):
        # --- TRAINING PHASE ---
        model.train()
        total_train_loss = 0.0
        for commands, labels in train_loader:
            commands, labels = commands.to(device, non_blocking=True), labels.to(device, non_blocking=True)

            optimizer.zero_grad()
            logits = model(commands).squeeze(-1)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            total_train_loss += loss.item()

        avg_train_loss = total_train_loss / len(train_loader)

        # --- VALIDATION PHASE ---
        model.eval()
        total_val_loss = 0.0
        correct = 0
        total = 0
        tp, fp, fn = 0, 0, 0

        with torch.no_grad():
            for commands, labels in val_loader:
                commands, labels = commands.to(device, non_blocking=True), labels.to(device, non_blocking=True)
                logits = model(commands).squeeze(-1)
                loss = criterion(logits, labels)
                total_val_loss += loss.item()

                preds = (torch.sigmoid(logits) > 0.5).float()
                correct += (preds == labels).sum().item()
                total += labels.size(0)

                tp += ((preds == 1) & (labels == 1)).sum().item()
                fp += ((preds == 1) & (labels == 0)).sum().item()
                fn += ((preds == 0) & (labels == 1)).sum().item()

        avg_val_loss = total_val_loss / len(val_loader)
        val_acc = (correct / total) * 100 if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        scheduler.step(avg_val_loss)

        print(f"Epoch {epoch:02d}/{epochs:02d} | "
              f"Train Loss: {avg_train_loss:.4f} | "
              f"Val Loss: {avg_val_loss:.4f} | "
              f"Val Acc: {val_acc:.2f}% | "
              f"F1-Score: {f1_score:.4f}")

        # Checkpoint ONLY when validation generalizes better
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(model.state_dict(), "omniguard_nlp.pth")
            print(f"  --> [SAVED] Optimal weights checkpointed to 'omniguard_nlp.pth'")

    print("-" * 75)
    print("[+] Training completed. Model validated on unseen distributions.")


if __name__ == "__main__":
    train_production_model()