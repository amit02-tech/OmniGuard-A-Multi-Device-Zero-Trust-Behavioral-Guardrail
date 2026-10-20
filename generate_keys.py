import os
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def generate_ed25519_keypair():
    print("[*] Generating Ed25519 Cryptographic Keypair...")

    # Generate the private key
    private_key = ed25519.Ed25519PrivateKey.generate()

    # Extract the public key
    public_key = private_key.public_key()

    # Serialize and save Private Key (Pretend this goes to the Mobile App)
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open("mobile_private.pem", "wb") as f:
        f.write(private_bytes)

    # Serialize and save Public Key (This stays with the OmniGuard Daemon)
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open("daemon_public.pem", "wb") as f:
        f.write(public_bytes)

    print("[+] Keys successfully written to mobile_private.pem and daemon_public.pem")


if __name__ == "__main__":
    generate_ed25519_keypair()