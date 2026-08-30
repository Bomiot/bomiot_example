from bomiot_token import encrypt_info, verify_info

print(encrypt_info())


COMMUNITY_KEY = "MDA6RTA6NEU6MTA61fJBMUIaiKXj6w3JctaeAroqCKStJYJO21-Mcx4MyJw5lQABNnjUH2mBlA=="
SPONSOR_KEY = "MDA6RTA6NEU6MTA61fJBMUIaiKXj6w3JctaeAroqGLuvJoRPwODFiW18OLrz9DeKBYKoNTY="

print(verify_info(COMMUNITY_KEY))