Project Overview:

City Limits is an educational simulation game designed to teach players the principles of effective traffic design and urban planning. Players are challenged to manage increasing traffic demands by implementing real-world intersection designs within a constrained grid. By selecting specific global cities, players experience localized traffic patterns driven by real-world data, observing how "rush hour" peaks and troughs impact their infrastructure choices. The goal is to optimize flow and achieve a target efficiency score to progress through increasingly complex urban layouts.

Game Play Mechanics:

City Selection & Real-Time Data: Before starting, players choose a city to represent. The game simulation begins at 12:00 AM, with car spawn rates governed by actual traffic density data for that specific location.
Level 1: 3x1 grid, 2 travel points.
Level 2: 3x2 grid, 3 travel points.
Level 3: 3x3 grid, 4 travel points (includes access to larger more advanced intersections)

Infrastructure Toolkit: Players can pick from many different types of intersections ranging from everyday ones to more unseen.



Scoring: Players must hit a target “flow rate” which is found using this equation

Flow Rate = (VAvg/Vlimit)X(TIdeal/TActual)x(1-TIdle/TActual)
Tech Stack:

Python
(More to come I’m not exactly sure yet exactly what I will need, but python is the main language)
Timeline:
Middle of February:
	Complete the core 2D grid system (starting with the 3x1 layout).
	Implement basic "Car" objects that can navigate from point A to point B.
	Finalize the Flow Rate math in the code to track speed and idle time.
Middle of March:
	Integrate real-world traffic data for your selected cities (e.g., Monroe, NY or Warsaw) to control car spawn rates.
	Expand the grid logic to handle the 3x2 and 3x3 layouts.
	Add the "Library of Intersections" so players can choose and place different designs.
End of March:
	Implement the "Rush Hour" mechanic where traffic density peaks based on the time of day.
	Add a user interface (UI) to display the current Flow Rate score and level progression.
	Create the win/loss conditions for moving between city levels.
End of Semester:
	Run final bug tests on both macOS and Windows to ensure the physics are consistent.
	Use PyInstaller to bundle the code into a standalone .app and .exe.
