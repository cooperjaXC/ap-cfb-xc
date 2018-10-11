import os, sys, requests, numpy
from bs4 import BeautifulSoup

appolllink = r"https://collegefootball.ap.org/poll"
staticespn = r"http://www.espn.com/college-football/rankings/_/week/6/year/2018/seasontype/2"
currentespnap = r"http://www.espn.com/college-football/rankings"

tfcounter = 0
tfive = []
while tfcounter < 25:
    tfcounter += 1
    tfive.append(tfcounter)


def apweeklyurlgenerator(week, year):
    """ Generate a URL link for a specific week of AP Rankings. Preseason = week 1 """
    finallist = ['final', 'f', 'complete', 'total']
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
    if week.lower() in finallist:
        finalurlexample = 'http://www.espn.com/college-football/rankings/_/week/1/year/2017/seasontype/3'
        url1 = 'http://www.espn.com/college-football/rankings/_/week/1/year/'
        seasontype = '/seasontype/3'
        url = url1 + year + seasontype
    else:
        url1 = r"http://www.espn.com/college-football/rankings/_/week/"
        url2 = r"/year/"
        url3 = r"'/seasontype/2"
        url = url1 + str(week) + url2 + year + url3
    return url


def pollgrabber(aplink):
    """ _ """
    r = requests.get(aplink)
    soup = BeautifulSoup(r.content, "html.parser")#, 'html5lib')
    # trsearch = soup.find_all('title')
    trsearch = soup.find_all('div')  # 'table-caption')
    # print trsearch
    print "- - - - - - - -"
    nodecounter = 0
    ##########
    strsearch = str(trsearch)
    # print strsearch
    return strsearch

def gettoptfive(websitestrsearch):
    """ _ """
    toptfive = {}
    nodecounter = 0

    strsearch = websitestrsearch
    print strsearch

    apsearchterm = "AP Top 25"  # 'class="number">1'
    for ranking in tfive:
        searchno1 = 'class="number">' + str(ranking) + '<'
        searchno2 = 'class="number">' + str(ranking+1) + '<'
        teamsearchstart = '<span class="team-names">'
        teamsearchend = '</span><abbr title='
        if apsearchterm.lower() in strsearch.lower() and searchno1.lower() in strsearch.lower():
            findap = strsearch.find(apsearchterm)
            findno1 = strsearch.find(searchno1)
            findno2 = strsearch.find(searchno2)
            outstring = strsearch[findno1:findno2]
            print ranking, outstring
            teamname = outstring[outstring.find(teamsearchstart)+len(teamsearchstart):outstring.find(teamsearchend)]
            nodecounter += 1
        else:
            teamname = "ERROR NO TEAM HERE"
        # ___
        if ranking in toptfive:
            print ranking, "ALREADY IN THE dictionary; missing", teamname
        else:
            toptfive[ranking] = teamname

    print "n =", nodecounter
    print toptfive
    for rank in toptfive:
        print rank, toptfive[rank]


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
    print strsearch

    apsearchterm = "AP Top 25"  # 'class="number">1'
    searchothers = 'class="title">Others receiving votes: </span>'
    searchno2 = r'</p></div>\n</div>\n<div'
    # searchno2 = r'</p></div>\n</div>\n</div>\n</div> <!-- // 50/50 Layout for Rankings'
    teamsearchstart = '<span class="team-names">'
    teamsearchend = '</span><abbr title='
    if apsearchterm.lower() in strsearch.lower() and searchothers.lower() in strsearch.lower():
        findap = strsearch.find(apsearchterm)
        findothers = strsearch.find(searchothers)
        findend = strsearch.find(searchno2)
        print findothers
        outstring = strsearch[findothers+len(searchothers):findend]
        print outstring
        print "String length:", len(outstring)
        outstringlist = outstring.strip().split(",")
        print outstringlist
        for othervote in outstringlist:
            if outstringlist[0] != othervote:
                othervote = othervote[1:]
            space = othervote.rfind(" ")
            pts = othervote[space+1:]
            team = othervote[:space]
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


# weekinquestion = apweeklyurlgenerator("Final", year=2012)  # Example of a top 25 tie that needs to be resolved.
weekinquestion = apweeklyurlgenerator(1, year=2018)

# pollgrabber(currentespnap)
gettoptfive(pollgrabber(weekinquestion))
# othersreceivingvotes(pollgrabber(weekinquestion))
