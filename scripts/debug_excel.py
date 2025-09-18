import pandas as pd

df = pd.read_excel('imports/mascouche_adresses.xlsx')
print('Sample data from Excel:')
for i in range(5):
    print(f'Ligne {i}:')
    print(f'  nomrue: {repr(df.iloc[i]["nomrue"])}')
    print(f'  OdoParti: {repr(df.iloc[i]["OdoParti"])}')
    print(f'  OdoSpeci: {repr(df.iloc[i]["OdoSpeci"])}')
    print()