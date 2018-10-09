

ttfcounter = 0
toptfive = {}
tfive = []
while ttfcounter < 25:
    ttfcounter += 1
    tfive.append(ttfcounter)
    toptfive[ttfcounter] = ""

# Empty dictionary with 25 slots
print toptfive

if 1 in toptfive:
    print True
