"""
ESPN API data from http://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings

BIG PROBLEM: The `cfbd` API does not have "others receiving votes."
However, [a doc on GitHub](https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b?permalink_comment_id=4376177)
leads to the rankings API endpoint for ESPN that *does* have others receiving votes data.
But, does it have historical rankings data?...

GitHub user @akeaswaran contributed the following re. historical data: (see https://github.com/cooperjaXC/ap-cfb-xc/issues/7#issuecomment-1709418119)
> http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/weeks/1/rankings/1?lang=en&region=us.
You can change the seasons and weeks values appropriately to get historical data,
and...you can get data on bowl/playoff games with a types value of 3 and weeks value of 1.

A few notes:
* Looks like a rankings value 1 in the URL is the AP poll -- you can manipulate this value for different polls if you want them.
* You won't need to use BeautifulSoup for this either -- just a requests.get() to grab the JSON and the json package to parse it.
* You'll have to make GET requests to the URLs provided in the $ref key of each record in the ranks array to get detailed team information.
* It does seem like there is receiving-votes data in there for your needs under the others array.
"""

espn_api = "http://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"
historical_espn_api_pth = "http://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2023/types/2/weeks/1/rankings/1"




