This is Python program using Flet (the UI on top of Flutter) to create a GUI program to manage a petanque tournament.

A petanque Tournament is known by its Name.

In a Tournament there are a number of Teams competing.  
A Team is know by its Name and gets assigned a Number for the Tournament.
A Team has at least 2 and maximum 3 Players. Each Player is known by its Name.

A Tournament consists of multiple Rounds followed by Semi-Finals and Finals. There are usually 3 rounds (not counting the Finals and Semi-finals) but less or more should be supported too. The number of rounds is requested in the GUI when starting a new Tournament.

In each Round, Teams are chosen randomly to compete one-on-one. While adding Teams to a Tournament a warning should be visible in the case that there are an odd number of Teams added. This allows the organizer (user) to add or remove a Team as needed to achieve an even number of Teams in the Tournament.

In a subsequent Round, pairs of Teams that competed each-other in earlier Rounds, may not be chosen to compete against each-other again. In Semi-Finals and Finals pairs of Teams that competed before can be repeated.

The winner of a Game is determined by the Team reaching 13 points first. This maximum points value should be adaptable in settings.

The score for both Teams in a Game is recorded, in order to calculate a positive or negative scoring-result for each Team in a Round. The scoring results is the number of points scored by the Team minus the number of points scored by the opposing Team. This is calculated and stored for both Teams for a Game.

After the Rounds of Tournament are played, a ranking of Teams is produced as follows:  
  1) Teams are ranked according to the most Games won (0, 1, ... to the number of Rounds)
  2) Within the Teams with the same amount of won Games, the Teams are ranked according to the sum of their scoring results (positive and negative)
  3) If Teams are still ranked equally, they are are further ranked by the biggest scoring result
  4) If there would still be equally ranked teams, they are finally ranked by their team number

From the ranking after the Rounds, the 4 top ranked teams are chosen. Those 4 are randomly assigned to play the 2 Semi-Finals.

The winner of a Semi-Final or Final is determined by the Team reaching 15 points first. This value can also be configured in a setting.

The winners of the Semi-Finals play each-other to determine 1st and 2nd place in the tournament.  
The losers of the Semi-Finals play each-other to determine 3rd and 4th place in the tournament. Other Teams are not ranked further.

The program should store all its data in structured files or file based databases, such that the program can be re-opened to continue with a previously created Tournament.  
The Team-names and their Player composition should be stored such that they can be reused in other Tournaments. The Team number differs per Tournament though.