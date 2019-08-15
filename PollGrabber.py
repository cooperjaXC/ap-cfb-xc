import os, sys, requests, numpy
from bs4 import BeautifulSoup

appolllink = r"https://collegefootball.ap.org/poll"
staticespn = r"http://www.espn.com/college-football/rankings/_/week/6/year/2018/seasontype/2"
currentespnap = r"http://www.espn.com/college-football/rankings"
defaultlink = currentespnap

tfcounter = 0
tfive = []
while tfcounter < 25:
    tfcounter += 1
    tfive.append(tfcounter)


def findnth(haystack, needle, n):
    """ <https://stackoverflow.com/questions/1883980/find-the-nth-occurrence-of-substring-in-a-string> """
    n = n-1
    parts = haystack.split(needle, n+1)
    if len(parts) <= n+1:
        return -1
    return len(haystack)-len(parts[-1])-len(needle)


def apweeklyurlgenerator(week, year):
    """ Generate a URL link for a specific week of AP Rankings. Preseason = week 1 """
    finallist = ['final', 'f', 'complete', 'total', 'last']
    prelist = ['preseason', 'initial', 'first', 'init', 'pre']

    # Format the year correctly
    year = str(year)
    if len(year) != 4:
        if len(year) == 2 and (year[0] == '1' or year[0] == '0'):
            # Assume the entry was an abreviation of a year. Add the 20__ before it.
            year = '20' + str(year)

    # Preseason?
    week = str(week)
    if week in prelist:
        week = '1'
    # If the week entered is higher than 16, assume user wants final rankings.
    try:
        if int(week) > 16:
            week = "final"
    except:
        pass

    # Generate the URL
    oldurl1 = r"http://www.espn.com/college-football/rankings/_/week/"
    url1 = r"http://www.espn.com/college-football/rankings/_/poll/1/week/"
    if week.lower() in finallist:
        oldfinalurlexample = 'http://www.espn.com/college-football/rankings/_/week/1/year/2017/seasontype/3'
        week1 = '1/year/'
        seasontype = '/seasontype/3'
        url = url1 + week1 + year + seasontype
    else:
        url2 = r"/year/"
        url3 = r"/seasontype/2"
        url = url1 + str(week) + url2 + year + url3
    return url
    # Should be the default URL: r"http://www.espn.com/college-football/rankings/_/poll/1/"


def pollgrabber(aplink):
    """ _ """
    r = requests.get(aplink)
    soup = BeautifulSoup(r.content, "html.parser")#, 'html5lib')
    # trsearch = soup.find_all('title')
    trsearch = soup.find_all('div')  # 'table-caption')
    # print trsearch
    print "- - - - - - - -"
    print aplink
    nodecounter = 0
    ##########
    strsearch = str(trsearch)
    # print strsearch
    return strsearch


def gettoptfive(websitestrsearch):
    """ _ """
    toptfive = {}
    nodecounter = 0
    inverserankings = {}

    strsearch = websitestrsearch
    print strsearch

    apsearchterm = "AP Top 25"  # 'class="number">1'
    for ranking in tfive:
        print "Ranking in top 25", ranking  ## Test print statement delete
        # Commented out search strs no longer used but kept in case of future troubleshooting.
        # searchno1 = 'class="number">' + str(ranking) + '<'
      #  searchno1 = '<td class="tight-cell Table2__td">' + str(ranking) + "<"
        # # 2019 edit
        searchno1 = '<td class="Table2__td">' + str(ranking) + "<"
        # searchno2 = 'class="number">' + str(ranking + 1) + '<'
      #  searchno2 = '<td class="tight-cell Table2__td">' + str(ranking+1) + "<"
        # # 2019 edit
        searchno2 = '<td class="Table2__td">' + str(ranking+1) + "<"
        # teamsearchstart = '<span class="team-names">'
        teamsearchstart = 'px" title="'
        # teamsearchend = '</span><abbr title='
        teamsearchend = '"/></a></span>'

        tieteamlist = []
        if apsearchterm.lower() in strsearch.lower() and searchno1.lower() in strsearch.lower():
            findap = strsearch.find(apsearchterm)
            findno1 = strsearch.find(searchno1)
            findno2 = strsearch.find(searchno2)
            outstring = strsearch[findno1:findno2]#+len(searchno2)]#]#Restore to the only ]
            # print ranking, outstring
            teamname = outstring[outstring.find(teamsearchstart)+len(teamsearchstart):outstring.find(teamsearchend)]
            print ranking, teamname
            nodecounter += 1

            # Search for a tie within this ranking's segment of strsearch
            tiecounter = 0

            #   #25 perpetually has this problem. You can search for the str 'Dropped from rankings:' if 25th team
            if ranking == 25:
                outstring = outstring[:outstring.find("Dropped from rankings:")]
            teamsinstrsearch = outstring.count(teamsearchstart)
            # tiecounter = teamsinstrsearch - 1 # Not really the case becasue the strsearch has a gob ton of teams
            if teamsinstrsearch > 1:
                print "!!!!!!!!!", teamname, "is in a tie!!!! Total teams at", ranking, ":", teamsinstrsearch
                searchno3 = 'class="number">' + str(ranking + 2) + '<'#you must put an exception jut in case there is greater than a 2 team tie; this only gets the ranking after 2 tied teams. If this was a 3 team tie, searching for x + 2 ranking would return None for the search
                findno3 = strsearch.find(searchno3)
                if findno3 == -1:
                    searchno3 = 'class="number">' + str(ranking + 3) + '<'
                    findno3 = strsearch.find(searchno3)
                    if findno3 == -1:
                        searchno3 = 'class="number">' + str(ranking + 4) + '<'
                        findno3 = strsearch.find(searchno3)
                tieoutstr = strsearch[findno1:findno3]
                print tieoutstr
            #Populate tieteamlist with all schools not initially set as teamname (like Texas A&M for final W 12).
            #   To do this, search thru tieoutstr string and find all instances of teamsearchstart. Append each that != teamname to tieteamlist

        else:
            previousranking = ranking - 1

            searchno1new = searchno1.replace(str(ranking), str(previousranking))
            searchno2new = searchno1.replace(str(ranking+1), str(ranking))  # Set end of the search as current ranking
                # yeah but what if we didn't do that. There is no current ranking that finds that search no. kee searchno2 the same to bound the back end of the new outstring?
            searchno3 = searchno2  # responding to the comment above. This bounds the back end of the outstr; previousranking + 2 or ranking + 1

            # teamsearchstart = 'px" title="' # same
            # teamsearchend = '"/></a></span>' # same

            if searchno1new in strsearch:
                # This is where the change has to come from. Cannot search for the first instance of the findno1.
                findno1new = strsearch.find(searchno1new)
                findno3 = strsearch.find(searchno3)
                noinfinity = strsearch[findno1new:findno3]  # noinfinity == outstring in above func but has an ending
                # use the 2nd entity of each team search strs to find next team
                teamname = noinfinity[findnth(noinfinity, teamsearchstart, 2)+len(teamsearchstart):
                                      findnth(noinfinity, teamsearchend, 2)]
                print ranking, teamname
            else:
                print searchno1new, "<-- search term aint in large strsearch neither"  ##This is a test print statement
                teamname = "ERROR NO TEAM HERE"

        # ___
        if ranking in toptfive:
            print ranking, "ALREADY IN THE dictionary; missing", teamname
            #function to append other team to the dict
        else:
            if len(tieteamlist) != 0:
                dictrank = toptfive[ranking]
                toptfive[ranking] = [teamname]
                for tieteam in tieteamlist:
                    dictrank.append(tieteam)
            else:
                toptfive[ranking] = teamname #should be [teamname]? would have to refigure code downstream if so


    print "n =", nodecounter
    print toptfive
    for rank in toptfive:
        team = toptfive[rank]
        print rank, team
        inverserankings[team] = rank
    print inverserankings
    return inverserankings

# here, make sure others receiving votes gets documented. Use function to jump off of last point possible in
#   pollgrabber function to split to get top 25 in one function and other votes in another.
    # Make sure in t25, you resolve ties.


def othersreceivingvotes(websitestrsearch):
    """ _ """
    tsixplus = {}
    nodecounter = 0
    tsixcounter = 26
    rankingdict = {}
    inverserankingdict = {}

    strsearch = websitestrsearch
    # print strsearch

    apsearchterm = "AP Top 25"  # 'class="number">1'
    searchothers = 'class="title">Others receiving votes: </span> <!-- -->'
    searchothersnewbold = 'class="fw-bold">Others receiving votes: </span>'  # Test for new formatting of this str
    # Test to see if new searchothers is the right way of searching now.
    searchothers = searchothersnewbold
    searchno2 = r'</p></div>\n</div>\n<div'  # </p></div>\n<div
    searchno2 = r'</p></div>\n<'#/div'
    # searchno2 = r'</p></div>\n</div>\n</div>\n</div> <!-- // 50/50 Layout for Rankings'
    searchno2 = r'</p><p><span class="fw-bold">'
    teamsearchstart = '<span class="team-names">'
    teamsearchend = '</span><abbr title='
    weirdstr = '<!-- -->'

    # Testing which search term is not being found:
    if apsearchterm.lower() in strsearch.lower():
        print apsearchterm, "is in this string; not the problem"
    else:
        print apsearchterm, "is not in this string and is the problem"

    if searchothers.lower() in strsearch.lower():
        print "var <strsearch> is in this string; not the problem"
    else:
        print "var <strsearch> is not in this string and is the problem"

    if apsearchterm.lower() in strsearch.lower() and searchothers.lower() in strsearch.lower():
        findap = strsearch.find(apsearchterm)
        findothers = strsearch.find(searchothers)
        findend = strsearch.find(searchno2)
        print findothers
        outstring = strsearch[findothers+len(searchothers):findend]
        # print outstring
        print "String length:", len(outstring)
        outstringlist = outstring.strip().split(",")
        # print outstringlist
        for othervote in outstringlist:
            if outstringlist[0] != othervote:
                othervote = othervote[1:]
            space = othervote.rfind(" ")
            pts = othervote[space+1:]
            team = othervote[:space]
            if weirdstr in team:
                team = str(team.replace(weirdstr, ""))
            print team, pts
            intpts = int(pts)
            if intpts not in tsixplus:
                tsixplus[intpts] = [team]
            else:
                tsixplus[intpts].append(team)
        print tsixplus
        pointorder = sorted(tsixplus, reverse=True)

        print "- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -"
        # Find average of ties
        for score in pointorder:
            teamlist = tsixplus[score]
            teamspervote = len(teamlist)
            if teamspervote == 1:
                rankingdict[tsixcounter] = teamlist[0]
                inverserankingdict[teamlist[0]] = tsixcounter
                tsixcounter += 1
            else:  # If there is a tie in votes:
                nextrank = tsixcounter
                lastrank = tsixcounter + teamspervote
                valstoaverage = range(nextrank, lastrank, 1)  # + 1, 1)
                designatedrank = numpy.mean(valstoaverage)
                # if designatedrank not in rankingdict:
                #     rankingdict[designatedrank] = teamlist[0]
                # elif designatedrank in rankingdict:
                for team in teamlist:
                    if team == teamlist[0]:
                        rankingdict[designatedrank] = [team]
                    else:
                        rankingdict[designatedrank].append(team)
                    inverserankingdict[team] = designatedrank
                tsixcounter += teamspervote
        print rankingdict
        print tsixcounter
        print inverserankingdict

        return inverserankingdict
    else:
        print "GRAVE ERROR"


def mergerankings(top25dict, othervotesdict):
    """ Merge the top 25 and beyond dictionaries into one dictionary by which we can assign points for XC scoring """
    rawmergeddict = {}

    for item in top25dict:
        rawmergeddict[item] = top25dict[item]
    for item in othervotesdict:
        rawmergeddict[item] = othervotesdict[item]

    print len(rawmergeddict), rawmergeddict

    return rawmergeddict


def orderedmergeddict(rawmergedic):
    """ _ """
    ordereddict = {}

    for team in rawmergedic:
        score = rawmergedic[team]
        if score not in ordereddict:
            ordereddict[score] = team
        else:
            ordereddict[score].append(team)

    print ordereddict
    return ordereddict


# # weekinquestion = apweeklyurlgenerator("Final", year=2012)  # Example of a top 25 tie that needs to be resolved.
# weekinquestion = apweeklyurlgenerator(10, year=2018)
#
# # pollgrabber(currentespnap)
# t25dict = gettoptfive(pollgrabber(weekinquestion))
# otherzdict = othersreceivingvotes(pollgrabber(weekinquestion))
#
# mergedict = mergerankings(t25dict, otherzdict)
# # scoreddict = orderedmergeddict(mergedict)
