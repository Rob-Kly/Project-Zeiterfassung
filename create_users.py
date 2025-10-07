from user_management import add_user

print(add_user("1", "Max", "Mustermann", nfc_code="04AABBCC", password="test123", role="admin"))
print(add_user("2", "Anna", "Mitarbeiter", nfc_code="04EEFFGG", password="1234", role="user"))
