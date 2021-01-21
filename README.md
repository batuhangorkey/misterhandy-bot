# A multi purpose discord bot written in Python
The bot has a Youtube player script and a hacking minigame from Fallout games. It could be a good exampe for people writing their first discord bot.  

The music player has a queue system, skip song and skip to seconds functions. It also has a user submitted playlist from which it plays semi-randomly according to like and dislike ratio. Playlist and misc data is stored in a sql database. 

It can work in multiple discord servers.

It needs a config.ini file in main directory. The config.ini structure is as follows:  
[Bot]  
Token=  
[Database]  
Host=  
UserID=  
Password=  
DatabaseName=  
