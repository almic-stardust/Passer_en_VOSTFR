#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
import re

# Initialization
global Debug
Debug = "no"
#Debug = "yes"



def Print_correct_usage():
	print()
	print("The first argument must be the video file to process.")
	print("The second argument can specify the output file.")
	print("The third argument can specify the audio language (English if not given).")
	print("The fourth and fifth arguments can specify the audio and subtitle tracks to keep.")
	print("If not given, the fourth and fifth arguments will be guessed by parsing the mpv output.")
	print()



def Format_filename(Filename):

	# [path/to/](Name).(Year).something.extension
	# Separate the actual filename from the path
	Name = Filename.split('/')[-1]
	Year = None

	# If the filename contains a year, we extract it with the string before it
	Match = re.search(r'\D(\d{4})\D', Name)
	if Match:
		Year = Match.group(1)
		Name = Name[:Match.start()].strip()

	# Remove hyphens, replace dots and spaces with underscores, replace multiple _ by only one
	Name = Name.replace(' - ', '_')
	Name = Name.replace(' ', '.').replace('.', '_')
	Name = re.sub(r'_+', '_', Name)

	# Capitalize the first letter and convert the rest to lowercase
	Name = Name[0].upper() + Name[1:].lower()

	if Year and Year != "1080":
		Formatted_filename = Name + "_" + Year + ".mkv"
	else:
		Formatted_filename = Name

	return Formatted_filename



def Determine_lang(Comment):
	Track_lang = ""
	# fr[ench], français, vf[i]
	if any(Word in Comment.casefold() for Word in ['fr', 'vf']):
		Track_lang = "fre"
	# [en]glish, anglais, vo
	elif any(Word in Comment.casefold() for Word in ['eng', 'vo', 'anglais']):
		Track_lang = "eng"
	else:
		print("Can’t determine the language of this track.")
		sys.exit(1)
	return Track_lang

def Parse_mpv_output(Mpv_output, Audio_lang):
	Audio_tracks = []
	Sub_tracks = []
	Count = 0
	Lines = Mpv_output.split('\n')

	for Line in Lines:
		if 'Audio' in Line or 'Subs' in Line:
			Count = Count + 1
		if 'Audio' in Line:
			if Debug == "no":
				print(Count, Line)
			Track_id = int(Line.split('--aid=')[1].split()[0])
			Track_lang = Line.split('--alang=')[1].split()[0] if '--alang=' in Line else None
			# TODO Tu veux travailler sur (eac3 6ch 48000Hz) et pas sur le commentaire
			#Codec = Line.split('\(')[1] if '\(' in Line else " "
			Comment = Line.split('\'')[1] if '\'' in Line else " "
			# Determine --alang for the lines that did not include it
			if Track_lang == None:
				Track_lang = Determine_lang(Comment)
			Audio_tracks.append((Track_id, Track_lang, Comment))
		elif 'Subs' in Line:
			if Debug == "no":
				print(Count, Line)
			Track_id = int(Line.split('--sid=')[1].split()[0])
			Track_lang = Line.split('--slang=')[1].split()[0] if '--slang=' in Line else None
			# « else " " » is necessary to avoid later testing Track[2].casefold() on a track
			# without commentary
			Comment = Line.split('\'')[1] if '\'' in Line else " "
			# Determine --slang for the lines that did not include it
			if Track_lang == None:
				Track_lang = Determine_lang(Comment)
			Sub_tracks.append((Track_id, Track_lang, Comment))

	# Select the best audio track for the desired language (dts > eac3 > ac3 > aac)
	Desired_lang_audio_tracks = [Track for Track in Audio_tracks if Track[1] == Audio_lang]
	if Debug == "yes":
		print("Audio tracks:")
		print(Audio_tracks)
		print("Desired_lang_audio_tracks =", Desired_lang_audio_tracks)
	if Desired_lang_audio_tracks:
		# TODO
		#Desired_lang_audio_tracks.sort(key=lambda Track: ('dts' not in Track[2], 'eac3' not in Track[2], 'ac3' not in Track[2], 'aac' not in Track[2]))
		Desired_lang_audio_tracks.sort(key=lambda x: ('dts' not in x[2], 'eac3' not in x[2], 'ac3' not in x[2], 'aac' not in x[2]))
		Selected_audio = Desired_lang_audio_tracks[0][0]
	else:
		Selected_audio = None

	if Debug == "yes":
		print("Subtitle tracks:")
		print(Sub_tracks)

	# Building a list of French subtitles, in case there’s only one track with slang="fre" and not
	# only “French” as a comment.
	French_subtitle_tracks = []
	for Track in Sub_tracks:
		if Debug == "yes":
			print(Track)
		# We remove the forced subtitles (Forcés, Forcé, Forced)
		if Track[1] == 'fre' \
		and not any(Word in Track[2].casefold() for Word in ['forced', 'forcé']):
			French_subtitle_tracks.append(Track)
	if Debug == "yes":
		print("French_subtitle_tracks =", French_subtitle_tracks)
	
	# Selecting full subtitles (Complets, Complet, complet, Full, FULL)
	Temp = []
	for Track in French_subtitle_tracks:
		if any(Word in Track[2].casefold() for Word in ['full', 'complet']):
			Temp.append(Track)
	if Temp:
		French_subtitle_tracks = Temp
	if Debug == "yes":
		print("French_subtitle_tracks =", French_subtitle_tracks)

	# Prefer SRT over other formats
	Temp = [Track for Track in French_subtitle_tracks if 'SRT' in Track[2]]
	if Temp:
		French_subtitle_tracks = Temp
	if Debug == "yes":
		print("French_subtitle_tracks =", French_subtitle_tracks)

	# Prefer “French (Parisian)” over “French (Canadian)”
	Temp = [Track for Track in French_subtitle_tracks if 'Parisian' in Track[2]]
	if Temp:
		French_subtitle_tracks = Temp
	if Debug == "yes":
		print("French_subtitle_tracks =", French_subtitle_tracks)

	# mpv creates a separate numbered list for each track type, but mkvmerge’s numbering includes
	# all track types in a single numbered list, with 0 for the video track id
	if French_subtitle_tracks:
		Selected_subtitle = len(Audio_tracks) + French_subtitle_tracks[0][0]
	else:
		Selected_subtitle = None

	return Selected_audio, Selected_subtitle



##################################################################
# Main

if len(sys.argv) < 2:
	Print_correct_usage()
	sys.exit(1)

Filename = sys.argv[1]
print()
if Debug == "no":
	print(Filename)
if Debug == "yes":
	print("sys.argv = ", sys.argv)
	print("len(sys.argv) =", len(sys.argv))
	print()

# No output file specified
if len(sys.argv) < 3:
	#import os +++ Output = '"' + os.getcwd() + '/' + Format_filename(Filename) + '"'
	Output = Format_filename(Filename)
elif sys.argv[2] == "AUTO":
	Output = Format_filename(Filename)
else:
	Output = sys.argv[2]

# No audio language specified
if len(sys.argv) < 4:
	Audio_lang = "eng"
else:
	Audio_lang = sys.argv[3]

# No audio tracks and subtitles specified
if len(sys.argv) < 5:

	# Man mpv:
	# --frames=0 loads the file, but immediately quits before initializing playback. Might be useful
	# for scripts which just want to determine some file properties.
	Mpv_command = ["mpv", "--frames=0", Filename]
	Mpv_process = subprocess.Popen(Mpv_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
	Mpv_output = Mpv_process.communicate()
	if Debug == "yes":
		print(Mpv_output)
	Audio, Subtitle = Parse_mpv_output(Mpv_output[0], Audio_lang)

else:
	try:
		Audio = int(sys.argv[4])
	except ValueError:
		print()
		print("If given, the 3rd argument must be an integer corresponding to the audio track.")
		Print_correct_usage()
		sys.exit(1)
	try:
		Subtitle = int(sys.argv[5])
	except ValueError:
		print()
		print("If given, the 4th argument must be an integer corresponding to the subtitle track.")
		Print_correct_usage()
		sys.exit(1)

print("Audio =", Audio, "              ", "Subtitles =", Subtitle)

# When the auto-detection of one track has failed
if Audio == None:
	print("Can’t find the audio track for", Audio_lang + ", select it manually.")
	sys.exit(1)
if Subtitle == None:
	print("Can’t find the French subtitle track, select it manually.")
	sys.exit(1)

Command = "mkvmerge -a " + str(Audio) + " -s " + str(Subtitle) \
				+ " --default-track " + str(Audio) + " --default-track " + str(Subtitle) \
				+ " \"" + Filename + "\" -o \"" + Output + "\""
if Debug == "yes":
	print(Command)

subprocess.call(Command, shell=True)
