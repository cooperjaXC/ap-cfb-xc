import os, sys, requests
from bs4 import BeautifulSoup

appolllink = r"https://collegefootball.ap.org/poll"
staticespn = r"http://www.espn.com/college-football/rankings/_/week/6/year/2018/seasontype/2"
currentespnap = r"http://www.espn.com/college-football/rankings"

tfcounter = 0
tfive = []
while tfcounter < 25:
    tfcounter += 1
    tfive.append(tfcounter)

# List of 1 to 25
print tfive


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

# def pinzest(pinlinklong):
#     r = requests.get(pinlinklong)
#     soup = BeautifulSoup(r.content, "html.parser")#, 'html5lib')
#     # print soup
#     print "------"
#     # trsearch = soup.find_all('title')
#     trsearch = soup.find_all('script')
#     for node2 in trsearch:
#         stringnode = str(node2)
#         # print stringnode
#         searchterm = "pinterestapp:source"
#         if searchterm in stringnode:
#             print stringnode
#             findsearchterm = stringnode.find(searchterm)
#             print findsearchterm
#             teststr = stringnode[findsearchterm:findsearchterm+250]
#             print teststr
#             print teststr[teststr.find('": "')+4:teststr.find('", "')]
#


def pollgrabber(aplink):
    """ _ """
    toptfive = {}
    r = requests.get(aplink)
    soup = BeautifulSoup(r.content, "html.parser")#, 'html5lib')
    # trsearch = soup.find_all('title')
    trsearch = soup.find_all('div')  # 'table-caption')
    # print trsearch
    print "- - - - - - - -"
    nodecounter = 0
    ##########
    strsearch = str(trsearch)
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
            print outstring
            teamname = outstring[outstring.find(teamsearchstart)+len(teamsearchstart):outstring.find(teamsearchend)]
            print teamname
            toptfive[ranking] = teamname
            nodecounter += 1
    ##########
    # for node2 in trsearch:
    #     stringnode = str(node2)
    #     # print stringnode
    #     if searchterm.lower() in stringnode.lower() and stringterm2 in stringnode.lower():
    #         # print stringnode
    #         findsearchterm = stringnode.find(searchterm)
    #         # print findsearchterm
    #         teststr = stringnode[findsearchterm:stringnode.find(stringterm2)+len(stringterm2)+77]
    #         print teststr
    # #         print teststr[teststr.find('": "')+4:teststr.find('", "')]
    #         nodecounter +=1
    print nodecounter
    print toptfive
    for rank in toptfive:
        print rank, toptfive[rank]


# weekinquestion = apweeklyurlgenerator("Final", year=2012)  # Example of a top 25 tie that needs to be resolved.
weekinquestion = apweeklyurlgenerator("Final", 2011)

# pollgrabber(currentespnap)
pollgrabber(weekinquestion)
