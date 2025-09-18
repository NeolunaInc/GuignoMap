from guignomap import database as db
print("helpers:", all(hasattr(db,n) for n in ["assign_addresses_to_team","get_unassigned_addresses","get_team_addresses"]))
try:
    ua = db.get_unassigned_addresses()
    print("Unassigned sample (top 3):", ua.head(3).to_dict(orient="records"))
except Exception as e:
    print("No unassigned yet or table missing:", e)