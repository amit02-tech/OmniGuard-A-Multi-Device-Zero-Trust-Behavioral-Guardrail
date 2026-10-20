import ctypes
import time


def simulate_rwx_allocation():
    print("[*] Benign RWX Simulator Started.")
    print("[*] Allocating PAGE_EXECUTE_READWRITE memory...")

    # Windows API Constants
    MEM_COMMIT = 0x1000
    MEM_RESERVE = 0x2000
    PAGE_EXECUTE_READWRITE = 0x40

    # Configure VirtualAlloc arguments
    kernel32 = ctypes.windll.kernel32
    kernel32.VirtualAlloc.restype = ctypes.c_void_p

    # Allocate 4096 bytes (1 page) of RWX memory
    address = kernel32.VirtualAlloc(
        ctypes.c_void_p(0),
        ctypes.c_size_t(4096),
        MEM_COMMIT | MEM_RESERVE,
        PAGE_EXECUTE_READWRITE
    )

    if address:
        print(f"[+] RWX Memory allocated successfully at {hex(address)}")
        print("[*] Sleeping for 60 seconds to await EDR interception...")
        time.sleep(60)
    else:
        print("[-] Memory allocation failed.")


if __name__ == "__main__":
    simulate_rwx_allocation()