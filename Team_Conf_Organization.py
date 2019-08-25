# Team Lists

# ACC
bostoncollege = "Boston College"
clemson = "Clemson"
duke = "Duke"
floridast = "Florida State"
georgiatech = "Georgia Tech"
louisville = "Louisville"
miami = "Miami (FL)"
unc = "North Carolina"
ncst = "NC State"
pittsburgh = "Pittsburgh"
syracuse = "Syracuse"
uva = "Virginia"
virginiatech = "Virginia Tech"
wakeforest = "Wake Forest"

# AAC
ucf = "UCF"
cincinnati = "Cincinnati"
uconn = "Connecticut"
ecu = "East Carolina"
houston = "Houston"
memphis = "Memphis"
navy = "Navy"
southflorida = "South Florida"
smu = "SMU"
temple = "Temple"
tulane = "Tulane"
tulsa = "Tulsa"
baylor = "Baylor"
iowast = "Iowa State"
kansas = "Kansas"
kansasst = "Kansas State"
oklahoma = "Oklahoma"
oklahomast = "Oklahoma State"
tcu = "TCU"
texas = "Texas"
texastech = "Texas Tech"
westvirginia = "West Virginia"

# B1G
illinois = "Illinois"
indiana = "Indiana"
iowa = "Iowa"
maryland = "Maryland"
michigan = "Michigan"
michiganst = "Michigan State"
minnesota = "Minnesota"
nebraska = "Nebraska"
northwestern = "Northwestern"
ohiost = "Ohio State"
pennst = "Penn State"
purdue = "Purdue"
rutgers = "Rutgers"
wisconsin = "Wisconsin"
uab = "UAB"

# CUSA
charlotte = "Charlotte"
fiu = "FIU"
floridaatlantic = "Florida Atlantic"
louisianatech = "Louisiana Tech"
marshall = "Marshall"
mtsu = "Middle Tennessee"
northtexas = "North Texas"
olddominion = "Old Dominion"
rice = "Rice"
southernmiss = "Southern Miss"
utep = "UTEP"
utsa = "UTSA"
westernkentucky = "Western Kentucky"

# Indep
liberty = "Liberty"
army = "Army"  # West Point
byu = "BYU"
umass = "Massachusetts"
newmexicost = "New Mexico State"
notredame = "Notre Dame"

# MAC
akron = "Akron"
ballst = "Ball State"
bowlinggreen = "Bowling Green"
buffalo = "Buffalo"
centralmichigan = "Central Michigan"
easternmichigan = "Eastern Michigan"
kentst = "Kent State"
miamioh = "Miami (OH)"
northernillinios = "NIU"
ohio = "Ohio"
toledo = "Toledo"
westernmichigan = "Western Michigan"

# Mountain West
airforce = "Air Force"
boisest = "Boise State"
coloradost = "Colorado State"
fresnost = "Fresno State"
hawaii = "Hawai'i"
nevada = "Nevada"
unlv = "UNLV"
newmexico = "New Mexico"
sandiegost = "San Diego State"
sanjosest = "San Jose State"
utahst = "Utah State"
wyoming = "Wyoming"

# Pac 12
arizona = "Arizona"
arizonast = "Arizona State"
cal = "California"
ucla = "UCLA"
colorado = "Colorado"
oregon = "Oregon"
oregonst = "Oregon State"
usc = "USC"
stanford = "Stanford"
utah = "Utah"
washington = "Washington"
washingtonst = "Washington State"

# SEC
alabama = "Alabama"
arkansas = "Arkansas"
auburn = "Auburn"
florida = "Florida"
georgia = "Georgia"
kentucky = "Kentucky"
lsu = "LSU"
olemiss = "Ole Miss"
mississippist = "Mississippi State"
missouri = "Missouri"
southcarolina = "South Carolina"
tennessee = "Tennessee"
texasam = "Texas A&M"
vanderbilt = "Vanderbilt"

# Sun Belt
appalachianst = "Appalachian State"
arkansasst = "Arkansas State"
coastalcarolina = "Coastal Carolina"
georgiasouthern = "Georgia Southern"
georgiast = "Georgia State"
louisiana = "Louisiana-Lafayette"
louisianamonroe = "Louisiana-Monroe"
southalabama = "South Alabama"
texasst = "Texas State"
troy = "Troy"


# Conferences
acc = [
    bostoncollege,
    clemson,
    duke,
    floridast,
    georgiatech,
    louisville,
    miami,
    unc,
    ncst,
    pittsburgh,
    syracuse,
    uva,
    virginiatech,
    wakeforest,
]

aac = [
    ucf,
    cincinnati,
    uconn,
    ecu,
    houston,
    memphis,
    navy,
    southflorida,
    smu,
    temple,
    tulane,
    tulsa,
]

bigxii = [
    baylor,
    iowast,
    kansas,
    kansasst,
    oklahoma,
    oklahomast,
    tcu,
    texas,
    texastech,
    westvirginia,
]

b1g = [
    illinois,
    indiana,
    iowa,
    maryland,
    michigan,
    michiganst,
    minnesota,
    nebraska,
    northwestern,
    ohiost,
    pennst,
    purdue,
    rutgers,
    wisconsin,
]

cusa = [
    uab,
    charlotte,
    fiu,
    floridaatlantic,
    louisianatech,
    marshall,
    mtsu,
    northtexas,
    olddominion,
    rice,
    southernmiss,
    utep,
    utsa,
    westernkentucky,
]

indep = [liberty, army, byu, umass, newmexicost, notredame]

mac = [
    akron,
    ballst,
    bowlinggreen,
    buffalo,
    centralmichigan,
    easternmichigan,
    kentst,
    miamioh,
    northernillinios,
    ohio,
    toledo,
    westernmichigan,
]

mtnwst = [
    airforce,
    boisest,
    coloradost,
    fresnost,
    hawaii,
    nevada,
    unlv,
    newmexico,
    sandiegost,
    sanjosest,
    utahst,
    wyoming,
]

pac12 = [
    arizona,
    arizonast,
    cal,
    ucla,
    colorado,
    oregon,
    oregonst,
    usc,
    stanford,
    utah,
    washington,
    washingtonst,
]

sec = [
    alabama,
    arkansas,
    auburn,
    florida,
    georgia,
    kentucky,
    lsu,
    olemiss,
    mississippist,
    missouri,
    southcarolina,
    tennessee,
    texasam,
    vanderbilt,
]

sunbelt = [
    appalachianst,
    arkansasst,
    coastalcarolina,
    georgiasouthern,
    georgiast,
    louisiana,
    louisianamonroe,
    southalabama,
    texasst,
    troy,
]

conferences = [acc, aac, bigxii, b1g, cusa, indep, mac, mtnwst, pac12, sec, sunbelt]
conferencedict = {
    "ACC": acc,
    "American": aac,
    "Big XII": bigxii,
    "Big Ten": b1g,
    "Conference USA": cusa,
    "Independent": indep,
    "MAC": mac,
    "Mountain West": mtnwst,
    "Pac 12": pac12,
    "SEC": sec,
    "Sun Belt": sunbelt,
}

onlyconferences = [acc, aac, bigxii, b1g, cusa, mac, mtnwst, pac12, sec, sunbelt]
onlyconferencesdict = {
    "ACC": acc,
    "American": aac,
    "Big XII": bigxii,
    "Big Ten": b1g,
    "Conference USA": cusa,
    "MAC": mac,
    "Mountain West": mtnwst,
    "Pac 12": pac12,
    "SEC": sec,
    "Sun Belt": sunbelt,
}

for confr in onlyconferencesdict:
    print confr, onlyconferencesdict[confr]
