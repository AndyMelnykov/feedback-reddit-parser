import getpass

import keyring

from credentials import SERVICE, REQUIRED_KEYS


def main():
    for key in REQUIRED_KEYS:
        keyring.set_password(SERVICE, key, getpass.getpass(f"{key}: "))


if __name__ == "__main__":
    main()
