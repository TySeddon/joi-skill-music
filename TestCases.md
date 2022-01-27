# Music Memory Box Test Cases

Given skill not active
when say "Hey Mycroft, play music"
then start music session

Given session is playing
when do nothing
then system plays X songs and exits

Given session is playing
when close web browser
then system will stop skill

Given session is playing and song is playing
when hit pause button in browser
then system will pause skill and if not resumed in 60 seconds, will stop skill

Given session is playing
when say "Hey Mycroft"
then music will pause and wait 5 seconds for instructions

Given waiting for instructions (after saying "Hey Mycroft")
when no instruction given
then music will resume

Given session is playing
when say "Hy Mycroft, stop"
then skill will stop

