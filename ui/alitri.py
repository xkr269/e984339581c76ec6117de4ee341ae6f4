import sys

boite_mots = sys.argv[1:]



liste_nombres = []


for caca in boite_mots:
    liste_nombres.append(int(caca))


liste_triee = []


while len(liste_nombres)>0:
    liste_triee.append(min(liste_nombres))
    liste_nombres.remove(min(liste_nombres))


print(liste_triee)

