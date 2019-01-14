import math

import PollGrabber
import Team_Conf_Organization as vars

# weekinquestion = PollGrabber.apweeklyurlgenerator("Final", year=2012)  # Example of a top 25 tie that needs to be resolved.
weekinquestion = PollGrabber.apweeklyurlgenerator(week='final', year=2018)
# weekinquestion = r"http://www.espn.com/college-football/rankings/_/poll/1/week/12/year/2017/seasontype/2"#deletethiswhenitworks
grabbedpoll = PollGrabber.pollgrabber(weekinquestion)
# grabbedpoll = PollGrabber.pollgrabber(r"http://www.espn.com/college-football/rankings/_/poll/1/week/11/year/2018/seasontype/2")

# pollgrabber(currentespnap)
t25dict = PollGrabber.gettoptfive(grabbedpoll)
otherzdict = PollGrabber.othersreceivingvotes(grabbedpoll)

mergedict = PollGrabber.mergerankings(t25dict, otherzdict)
# scoreddict = orderedmergeddict(mergedict)

conferencepointsdict = {"ACC": [], "American": [], "Big XII": [], "Big Ten": [], "Conference USA": [],
                        "Independent": [], "MAC": [], "Mountain West": [], "Pac 12": [], "SEC": [], "Sun Belt": []}

mistakedict = {vars.miami: "Miami", vars.texasam: "Texas A&amp;M;"}

for conference in vars.conferencedict:
    confscore = []
    teamlist = vars.conferencedict[conference]
    print conference, len(teamlist), teamlist
    # for teem in conferencedict[conference]:
    #     print team
    for team in teamlist:
        # Make sure odd names like Texas A&M and Miami (FL) are taken care of
        if team in mistakedict:
            team = mistakedict[team]
        # Did teams receive votes in this week's AP Poll?
        if team in mergedict:
            indivscore = mergedict[team]
            print team, indivscore
            # Append them to the correct conference's list of scores
            confscore.append(indivscore)
            # conferencepointsdict[conference].append(indivscore)
    confscore.sort()
    print conference, "score:", confscore  # .sort()
    conferencepointsdict[conference] = confscore
print conferencepointsdict

fourscoredict = {}
fivescoredict = {}

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
    print conf, ":", scoredteams, "teams scored"
    fourscoredict[conf] = foursum
    print "| 4score:", foursum
    fivescoredict[conf] = fivesum
    print "| 5score", fivesum
    print "| ALL:", pointlist

print fourscoredict
print fivescoredict


