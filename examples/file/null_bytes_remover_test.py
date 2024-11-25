#!/usr/bin/env python3
try:
    import common
except:
    pass
from pawnlib.output.file import NullByteRemover


def create_test_file(file_path, size_in_bytes, null_byte_positions):
    """
    Create a test file with specified size and null bytes at given positions.

    :param file_path: Path to the test file to be created.
    :param size_in_bytes: Total size of the file in bytes.
    :param null_byte_positions: List of byte positions where null bytes should be inserted.
    """
    with open(file_path, 'wb') as f:
        for i in range(size_in_bytes):
            if i in null_byte_positions:
                f.write(b'\x00'*10)  # Write a null byte
            else:
                f.write(b'A')  # Write a regular byte (e.g., 'A')

def main():
    # Create test files
    test_files = [
        ("test_file1.txt", 1024, [0, 20, 30]),  # 1 KB file with null bytes at positions 10, 20, 30
        ("test_file2.txt", 2048, [50, 100, 150]), # 2 KB file with null bytes at positions 50, 100, 150
        ("test_file3.txt", 512, [5, 15]),         # 512 bytes file with null bytes at positions 5, 15
    ]

    for file_name, size, null_positions in test_files:
        create_test_file(file_name, size, null_positions)
        print(f"Created {file_name} with size {size} bytes and null bytes at positions {null_positions}")

    # Now we can use the NullByteRemover class to remove null bytes from these files
    remover = NullByteRemover([file_name for file_name, _, _ in test_files])
    remover.remove_null_bytes()
    remover.print_report()

if __name__ == "__main__":
    main()
