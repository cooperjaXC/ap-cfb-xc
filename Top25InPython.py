import math

import PollGrabber
import Team_Conf_Organization as vars

# Target Week
weekinquestion = PollGrabber.dateprocessing(
    week='current',  # "preseason",  # 'final', # 4,#
    year=2019

    # # Ties
    # week="Final", year=2012  # Example of a top 25 tie  # 5 Georgia & Texas A&M
    # week=4, year=2019  # Another example of a top 25 tie  # 13 Penn St & Wisconsin
    # week=2, year=2019  # Example of a tie at number 25  # Nebraska & Iowa St. # ORVs should now start at 27+.
    # week=6, year=2019  # Another tie at rank number 25  # Texas A&M & Michigan St. 25.5, California at 27

    # # Other Troubleshooting
    # # Note: 2013 and before may error with "GRAVE ERROR" because ESPN does not have data for ORVs.
    # week='final', year=2003  # Year both Miami FL and Miami OH finished in top 10. Last final appearance there for M(OH)
)

generated_url = PollGrabber.apweeklyurlgenerator(weekinquestion)

grabbedpoll = PollGrabber.pollgrabber(generated_url)
# grabbedpoll = PollGrabber.pollgrabber('http://www.espn.com/mens-college-basketball/rankings')  # for basketball

# Get a dictionary of the top 25 teams
t25dict = PollGrabber.gettoptfive(grabbedpoll)

# Check that ESPN will have ORVs. Only for 2014 and on.
if int(weekinquestion[1]) < 2014:
    print("Warning: Others Receiving Votes not stored by ESPN before the 2014 season.")
    mergedict = t25dict
else:
    # Get a dictionary of the "others receiving votes" and their ranks.
    otherzdict = PollGrabber.othersreceivingvotes(grabbedpoll, t25dict)

    mergedict = PollGrabber.mergerankings(t25dict, otherzdict)
    # scoreddict = orderedmergeddict(mergedict)

conferencepointsdict = {
    "ACC": [],
    "American": [],
    "Big XII": [],
    "Big Ten": [],
    "Conference USA": [],
    "Independent": [],
    "MAC": [],
    "Mountain West": [],
    "Pac 12": [],
    "SEC": [],
    "Sun Belt": [],
}

mistakedict = {vars.miami: "Miami", vars.texasam: "Texas A&amp;M"}  # "Texas A&amp;M;"

# Begin operations

for conference in vars.conferencedict:
    confscore = []
    teamlist = vars.conferencedict[conference]
    print(conference, len(teamlist), teamlist)
    # for teem in conferencedict[conference]:
    #     print(team)
    for team in teamlist:
        # Make sure odd names like Texas A&M and Miami (FL) are taken care of
        if team in mistakedict:
            team = mistakedict[team]
        # Did teams receive votes in this week's AP Poll?
        if team in mergedict:
            indivscore = mergedict[team]
            print(team, indivscore)
            # Append them to the correct conference's list of scores
            confscore.append(indivscore)
            # conferencepointsdict[conference].append(indivscore)
    confscore.sort()
    print(conference, "score:", confscore)  # .sort()
    conferencepointsdict[conference] = confscore
print(conferencepointsdict)

fourscoredict = {}
fivescoredict = {}

# Get the max score for downstream pandas work
#   If max >= 100, more digits needed in the print(ut for the pandas table.)
maxfourscore = 0
maxfivescore = 0

# _____ <- what does this next section do?
for conf in conferencepointsdict:
    pointlist = conferencepointsdict[conf]
    pointlist.sort()

    scoredteams = len(pointlist)
    if scoredteams > 3:
        foursum = math.fsum(pointlist[:4])
    else:
        foursum = None
    if scoredteams > 4:
        fivesum = math.fsum(pointlist[:5])
    else:
        fivesum = None
    print(conf, ":", scoredteams, "teams scored")

    fourscoredict[conf] = foursum
    print("| 4score:", foursum)
    # Check on maxfourscore & set it to = conference's score if conference's score is greatest yet.
    if foursum is not None and foursum > maxfourscore:
        maxfourscore = foursum

    fivescoredict[conf] = fivesum
    print("| 5score", fivesum)
    print("| ALL:", pointlist)
    # Check on maxfivescore & set it to = conference's score if conference's score is greatest yet.
    if fivesum is not None and fivesum > maxfivescore:
        maxfivescore = fivesum
