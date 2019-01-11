import sys

boite_mots = sys.argv[1:]

boite_nombres = []

for mot in boite_mots:
    boite_nombres.append(int(mot))


boite_triee = []


while len(boite_nombres)>0:
    plus_petit_nombre = min(boite:wq
_nombres)
    boite_triee.append(plus_petit_nombre)
    boite_nombres.remove(plus_petit_nombre)
			

print(boite_triee)


