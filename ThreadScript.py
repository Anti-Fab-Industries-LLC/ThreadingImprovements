#!/usr/bin/env python3
from __future__ import annotations
from collections.abc import Callable # https://docs.python.org/3/library/collections.abc.html
import re # https://docs.python.org/3/howto/regex.html#regex-howto
import sys # https://docs.python.org/3.13/library/sys.html
import math # https://docs.python.org/3/library/math.html

'''
Bounty Board:
TODO: Refactor definitions using annotations
	- https://docs.python.org/3/howto/annotations.html
TODO: Strict types on functions
	- Almost none of the functions filter by the required data type
TODO: Modal Correction
	- This script is not intended to be used with modal Gcode. It needs to be tested for that application.
	- Incorporate a log of the last value that the parent file gives for each axis
TODO: File name handling needs to be integrated into extract fuction
	- Ammend the Locating features dictionary to be have a "Prepend" and "Apend" where the respective program name and end line are stored
TODO: Implement logging and error function
TODO: Implement input handling function
	- User input
	- Freecad Programatic input with path objects
TODO: Fix type problems
	- Strict typing needs to be enforced
	- When an object leaves the area it's being ammended set it properly according to a type table
	- Type Table: An object that contains the ideal types for array members. Ex: a table to make sure Locating features is only a float where it needs to be
TODO: Convert all adjust the liberal usage of floats to be higher precision.
	- Math at the scale of mm should be done at the scale of microns
	- This will cause any inacuracy of the float to be a margin of safty more precise
'''

'''
Workflow
1. Read source ReadFile line by line
	a. Store program name
		- Not implemented
	b. Each line that contains G81 gets parses NXYZR values into LocatingFeatures dictionary
		I. Settup function sets the correct tool and speed
			- Isn't status aware. Relies on spindle status bool.
			- Appended to output list
		II. Thread GCode lines are appended
			- Appended to output list 
	c. Store each non G81 line into list
	d. Store END line
2. Write list to WriteFile
'''

'''
This program was written by Willow Leahy for Anti-Fab Industries LLC on November 7, 2026
If you need to contact her sent an email to <willow@antifab.org>
Copyright © 2026 Anti-Fab Industries, LLC
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
'''

'''
How to use this tool:
	This is a script to add gcode for a threading operation on a mill.
	It reads the EIA format of gcode for the Tree 325 with a Dyanapath Delta 20 M
	A postproccesor is available to format FreeCAD CAM path object at Anti-Fab Industries LLC, Refactored_Dynapath_d20_post on github
	The Gcode the user feeds this tool must include the safe hight as the R value and the start Z plane as as the Z value
'''

'''
# TODO: For logging progress
def scriptLogger(inside: str):
	sys.stderr.write(inside)
	pass
'''

'''
# TODO: Parses the input
class UserInput: # https://docs.python.org/3/reference/compound_stmts.html#class
	Later down the road this will have the ability to ask the user questions about the thread to be generated.
	For now all is hardcoded
	Can also read thread details from a standardized file so that the user can specify thread types from selected geometry in freecad
		That feature is needed for way dowwn the road when this script my be merged with exoisting freecad infrastructure
'''

# Puts the correct alpha code in the correct format. Modified from Refactored_Dynapath_d20_post_patch_Oct_16.py
def fmt_value(key, value:float):
	# Ammend to also accomodate formatting prepending zeros. Ex: G02, M06
	match key:
		case "X" | "Y" | "Z" | "I" | "J" | "K" | "R" | "Q" | "N":
			return round(value, 3)
		case "F" | "S" | "T" | "H" | "D":
			return round(value, 0)
		case _:
			return value

# SurfaceFeetMin to RPM Calculator
def Speed (ToolDetails):

	ToolDiameter = ToolDetails["Diameter"]
	SurfaceFeetMin = ToolDetails["SurfaceFeetMin"]

	RPM = (SurfaceFeetMin * 12)/(ToolDiameter * math.pi)
	return int(math.floor(RPM))

# InchTooth to MmMin Calculatior
def Feed (RPM, ToolDetails, ThreadDetails):

	ThreadMajorDiameter = ThreadDetails["MajorDiameter"]
	FluteCount = ToolDetails["FluteCount"]
	ToolDiameter = ToolDetails["Diameter"]
	Chipload = ToolDetails["ChipPerTooth"]

	NAFR = RPM * Chipload * FluteCount
	AFR = NAFR*(ThreadMajorDiameter - ToolDiameter)/ThreadMajorDiameter
	return math.floor(AFR*25.4)

# Add Line to set from passed variables and return line number float
def AddLine(GCodeContainer, **Attributes):

	Attributes["N"] = float(Attributes["N"])
	Attributes["N"] += 0.001 # Doesn't actually change the passed value off the argument passed via N=

	for key, value in Attributes.items():
		if key == "N": value + 0.001 
		value = fmt_value(key, value) # Is there a better way to integrate this definment?
		Attributes.update({f"{key}": value})

	GCodeContainer.append( # Pass all compiled Gcodes in list format through GCodeContainer. Should do N first but always double check
		"".join(
			f"{key}{value}"
			for key, value in Attributes.items()
			if (value is not None) and (value != "")
			)
	)

	return Attributes["N"]

# Add tool change and spindle ramp 
def Settup(ToolDetails, SpindleStatus, LocatingFeatures, step=500, dwell=2.0):

	FinalSpeed = int(LocatingFeatures["S"])
	Speed = 0
	Settup = list()
	direction = "CW"
	LocatingFeatures["N"] = float(LocatingFeatures["N"])

	if SpindleStatus["ToolChange"]:
		Mcode = "6"
		LocatingFeatures["N"] = AddLine(GCodeContainer=Settup, N=LocatingFeatures["N"], M=Mcode, T=ToolDetails["ToolNumber"])
		SpindleStatus["ToolChange"] = False

	if not SpindleStatus["AtSpeed"]:
		if direction == "CW":
			MCode = "3"
		elif direction == "CCW":
			MCode = "4"
		GCode = "4" # Spindle dwell

		for iterator in range(math.floor(FinalSpeed/step)):
			LocatingFeatures["N"] = AddLine(GCodeContainer=Settup, N=LocatingFeatures["N"], M=MCode, S=Speed)
			LocatingFeatures["N"] = AddLine(GCodeContainer=Settup, N=LocatingFeatures["N"], G=GCode, X=2)
			Speed += step
			

		LocatingFeatures["N"] = AddLine(GCodeContainer=Settup, N=LocatingFeatures["N"], M=MCode, S=FinalSpeed)
		SpindleStatus["AtSpeed"] = True

	return Settup, LocatingFeatures, SpindleStatus

# Makes the gcode to shim in
def GenerateThread (LocatingFeatures, ToolDetails, ThreadDetails, SpindleStatus):

	StartZPlane = float(LocatingFeatures["Z"]) # Distance from part 0 Z plane to the start plane of the hole
	Feed = LocatingFeatures["F"]
	Line = LocatingFeatures["N"]
	Pitch = ThreadDetails["Pitch"]
	ToolZLength = ToolDetails["ZLength"]
	Thread = list()
# +(2*float(Pitch)) # Aircutting lead in
	ThreadZDepth = ThreadDetails["ZDepth"]	
	EndZPlane = float(ThreadDetails["DistanceFromZero"] - ThreadZDepth) # Absolute coordinate from the start plane of the hole
	Count = math.ceil(ThreadZDepth/Pitch) # Over cuts. This means the thread needs to be bottom alligned so that the tool will not crash.
	StartZ = EndZPlane + (Count * float(Pitch)) + (2 * float(Pitch)) # Aircutting lead in # Ensure that the user knows to always set the final G81 depth as the start of the hole 

	# G22 and G23 are inposition detect G2 and G3. This is important for the quality of the thread
	if ThreadDetails["Type"] == "Internal":
		pass
	elif ThreadDetails["Type"] == "External":
		print("Bad Thread Type specified")
		sys.exit(1)
	else:
		print("Bad Thread Type specified")
		sys.exit(1)

	# Arc Type
	if ThreadDetails["Direction"] == "CW":
		GCode=22
	elif ThreadDetails["Direction"] == "CCW":
		GCode=23
	else:
		print("Bad Thread Direction specified")
		sys.exit(1)

	'''
	Thread will be computed from ending z plane up to starting z plane
	Then it will be executed from the Starting z plane to the ending z plane
	with a G0 feed back to the origin
	Then a rapid to safe Z height
	'''
	
	# Thread.extend(
	Temp = Settup(
		LocatingFeatures=LocatingFeatures,
		SpindleStatus=SpindleStatus,
		ToolDetails=ToolDetails
		) # Appends the list returned by settup to Output)
	Thread.extend(Temp[0])
	Line = Temp[1].get("N")
	SpindleStatus = Temp[2]

	# Go to origin x, y, z
	CurrentZ = StartZ
	Line = AddLine(
		GCodeContainer=Thread,
		N=Line,
		G=0,
		X=float(LocatingFeatures["X"]),
		Y=float(LocatingFeatures["Y"]),
		Z=CurrentZ,
		F=Feed
		)

	# All thread sections
	ArcRadius = ThreadDetails["MajorDiameter"] - (float(ToolDetails["Diameter"])/2)
	ArcX = float(LocatingFeatures["X"]) + ArcRadius
	ArcY = float(LocatingFeatures["Y"]) + ArcRadius
	for i in range(Count+3):
		CurrentZ = StartZ-(i*Pitch)
		Line = AddLine(
			GCodeContainer=Thread,
			N=Line,
			G=GCode,
			X=ArcX,
			Y=ArcY,
			Z=CurrentZ,
			F=Feed
			)
		
	# Feed to origin x, y and bottomz
	Line = AddLine(
		GCodeContainer=Thread,
		N=Line,
		G=1,
		X=float(LocatingFeatures["X"]),
		Y=float(LocatingFeatures["Y"]),
		Z=EndZPlane,
		F=Feed
		)

	# Stop Spindle
	Line = AddLine(
		GCodeContainer=Thread,
		N=Line,
		M=5,
		)
	SpindleStatus["AtSpeed"] = False

	# feed up to orgin z
	Line = AddLine(
		GCodeContainer=Thread,
		N=Line,
		G=1,
		Z=StartZ,
		F=Feed
		)

	# Rapid up to safe Z
	SafeZ = float(LocatingFeatures["R"]) # R is the plane the the canned cycle starts at. The user should define this value as the safe plane
	Line = AddLine(
		GCodeContainer=Thread,
		N=Line,
		G=0,
		Z=StartZ
		)

	return Thread

# Parsing source gcode
def Extract (ToolDetails, ThreadDetails):

	ReadFile = open("./THREADsettup.gcode", mode="rt")
	Output = list()
	G81Match = ""
	SpindleStatus = {"ToolChange":True, "AtSpeed":False} # Tool change True means it need to be changed
	LocatingFeatures = {}
	LocatingFeatures.update({"S":Speed(ToolDetails=ToolDetails)})
	LocatingFeatures.update({"F":Feed(RPM=LocatingFeatures["S"], ToolDetails=ToolDetails, ThreadDetails=ThreadDetails)})

	for Line in ReadFile.readlines():
		Gcode = "G81"
		G81Match = re.search(pattern=Gcode, string=str(Line))
		LocatingFeatures.update({"N":"", "X":"", "Y":"", "Z":"", "R":""})
		
		if G81Match:
			'''
			Matches any part of the Line that contains the combination of ReliventValues and ReliventPattern
			Then stuffs the numeric sections into a dictionary called LocatingFeatures.
			Each key of the dictionary is sequential element of ReliventValues
			Each value of the dictionary is the respective regex match of the ReliventPattern
			''' 
			ReliventValues = ("N", "X", "Y", "Z", "R")
			PositionalPattern = str(r"[0-9]{1,3}\.[0-9]{1,3}") # Raw strings need to used so that the "\" can be used to escape regex "."
			ReliventPattern = (str("[0-9]{4}"), PositionalPattern, PositionalPattern, PositionalPattern, PositionalPattern)
			
			for element in zip(ReliventValues, ReliventPattern): # Should probably use dict.items() here but it seems to work rn
				Data = re.search(pattern=str(element[0]+element[1]), string=str(Line)) # Locates the correct value with the string to ensure the program grabs the correct value
				if Data: 
					container = re.search(pattern=str(element[1]), string=Data.group(0)) # Drops the string to then grab the numeric section and adds the key value pair to the LocatingFeatures dictionary
					LocatingFeatures[str(element[0])] = str(container.group(0))

			Output.extend(GenerateThread(
				LocatingFeatures=LocatingFeatures,
				ToolDetails=ToolDetails,
				ThreadDetails=ThreadDetails,
				SpindleStatus=SpindleStatus
				)) # Takes the LocatingFeatures dictionary and generates thread thenn appends the whole line of gcode to Output

		else:
			Data = re.search(pattern=str("^N.*$"), string=Line) # TODO: Doesn't match program name
			if Data:
				# Output.append(Data.group(0))
				pass

	ReadFile.close()
	return Output

if __name__ == "__main__": # Includes so that is file can be used as a library too. This logic should be made more complicated when integrating into FreeCAD CAM workbench.

	# Execution
	with open("./THREAD.gcode", mode="wt") as WriteFile: # https://docs.python.org/3/builtins/functions.html#open

		ThreadDetails = {
			"MinorDiameter":float(0.202), # in
			"MajorDiameter":float(0.219949), # in
			"Pitch":float(0.7874015748), # Threadmm
			"Type":"Internal",
			"Direction":"CW",
			"ZDepth":float(19.0500), # mm
			"DistanceFromZero":0 # mm
			}

		ToolDetails = {
			"Name":"SPTM182LA",
			"Diameter":float(0.182), # in
			"ZLength":float(19.685), # mm
			"FluteCount":int(4),
			"SurfaceFeetMin":int(100), # ft
			"ChipPerTooth":float(.0005), # in
			"DepthOfCut1":float(1.00), # %
			"DepthOfCut2":(float(0.65), float(0.35)), # %
			"DepthOfCut3":(float(0.50), float(0.30), float(0.20)), # %
			"DepthOfCut4":(float(0.40), float(0.27), float(0.20), float(0.13)), # %
			"ToolNumber": int(6) # The tool holder catelouge number. Sycronnized with tool table in head unit.
			}

		# For dubugging
		for times in range(len(Extract(ToolDetails, ThreadDetails))):
			print(Extract(ToolDetails, ThreadDetails)[times]) # Print is handling Line feed right now so patch that

		ScriptName = "(THREAD)\r\n" # Max of 7 chars
		WriteFile.write(ScriptName) # TODO: File name handling needs to be integrated into extract

		for Line in Extract(ToolDetails, ThreadDetails):
			WriteFile.write(f"{Line}\r\n") # <CR><LF> is requred between each line for EIA programming. <CR> = \r <LF> = \n

		WriteFile.write("N999M0\r\n")
		WriteFile.write("END")
			
		WriteFile.close() # https://docs.python.org/3/builtins/stdtypes.html#generator.close
