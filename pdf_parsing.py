from typing import Iterable, Union, Tuple, List
import pandas as pd
import pandas.core.series
from pandas import DataFrame, Series
import colorama
import re
from datetime import datetime


pd.set_option('display.expand_frame_repr', False)
# We will need a way more advanced parsing system in the future.
_MESSAGE_DICT = {
	"replacement": ("statt", "Stundentausch", "vorgezogen", "verlegt von", "verschoben von"),
	"cancellation": ("Ausfall", "verschoben auf", "verlegt", "verschoben"),
	"room-change": ("Raumänderung",)
}


class _SkipObject(Exception):
	pass


class _TableFailure:
	def __init__(self, table_index: int, reason: str):
		self.table_index = table_index
		self.reason = reason

	def to_dict(self) -> dict:
		return {
			"type": "table",
			"tableIndex": self.table_index,
			"reason": self.reason
		}


class _RowFailure(_TableFailure):
	def __init__(self, table_index: int, row_index: int, reason: str, last_parsed_row: Union[dict, None]):
		super().__init__(table_index, reason)
		self.row_index = row_index
		self.last_parsed_row = last_parsed_row

	def to_dict(self) -> dict:
		return {
			"type": "row",
			"tableIndex": self.table_index,
			"rowIndex": self.row_index,
			"reason": self.reason,
			"lastParsedRow": self.last_parsed_row
		}


def _parse_replacement(to_parse: str, always_from=False) -> Union[Tuple[Union[str, None], Union[str, None]], None]:
	if search_obj := re.search(r"\+?(?P<to>[\w\s,Ä-ü\-]+)\((?P<from>[\w\s,Ä-ü\-]+)\)", to_parse):  # ","-botch
		change_to = search_obj.groupdict()["to"]
		change_from = search_obj.groupdict()["from"]
		return re.sub(r"\s", "", change_from), re.sub(r"\s", "", change_to)
	elif search_obj := re.search(r"\((?P<from>.+)\)", to_parse):
		return search_obj.group(1).strip().replace("\n", ""), None
	elif len(stripped_field := to_parse.strip().replace("\n", "")) > 0:
		# (Herr Blabla) -> cancellation (how it should be)
		# DEU -> cancellation (how it is in subject)
		# because of upper mentioned problem we have to add an edge case for subject
		if always_from:
			return stripped_field, None
		else:
			return None, stripped_field
	else:
		return None


# todo refactor all the parsers into there own file
def parse_date(row_0: pandas.core.series.Series) -> Union[str, None]:
	for cell in row_0:
		if search_obj := re.search(r"\d\d\.\d\d\.\d\d\d\d", cell):
			return datetime.strptime(search_obj.group(0), "%d.%m.%Y").strftime("%Y-%m-%d")
	return None


def _parse_classes(class_cell: str) -> Union[List[str], None]:
	if len(search_results := re.findall(r"[A-z]+ ?\d+", class_cell.strip().replace("\n", ""))) > 0:
		return [search_result.replace(" ", "") for search_result in search_results]
	else:
		return None


def _parse_lesson(time_cell: str) -> Union[int, None]:
	try:
		if search_obj := re.search(r"\d(?=\.)", time_cell):  # not expecting 10
			return int(search_obj.group(0))
		else:
			# int is raising ValueError when it cant pass string. dont want to write code twice
			raise ValueError
	except ValueError:
		return None


def _parse_message(message_cell: str) -> Union[str, None]:
	if len(re.sub(r"\s", "", message_cell)) == 0:
		return None

	stripped_message_cell = message_cell.strip().replace("\n", "")
	for action, aliases in _MESSAGE_DICT.items():
		for alias in aliases:
			if alias in stripped_message_cell:
				return action

	return "other"


def _guess_action(teacher_change_from: Union[str, None], teacher_change_to: Union[str, None]) -> str:
	if teacher_change_from and teacher_change_to:
		return "replacement"
	elif teacher_change_from:
		return "cancellation"
	elif teacher_change_to:
		# return "cancellation"  # i dont know why i had that in the first place
		return "room-change"
	else:  # probably never the case
		return "other"


def _on_error(error: _TableFailure):
	if isinstance(error, _RowFailure):
		print(colorama.Fore.RED + f"Parsing error at table {error.table_index} at row {error.row_index} "
								f"because {error.reason}.")
	else:
		print(colorama.Fore.RED + f"Parsing error at table {error.table_index} because {error.reason}")


def parse_dataframes(data_frames: Iterable[DataFrame]) -> dict:
	colorama.init(autoreset=True)  # for color in error_msgs
	# print(data_frames)

	cur_date = None
	last_parsed = None
	data_list = []
	parsing_failures = []
	for df_index, df in enumerate(data_frames, start=1):
		# checking if table has proper size
		# print(df)
		if len(df.columns) != 6:
			parsing_failure = _TableFailure(df_index, "amount of columns")
			_on_error(parsing_failure)
			parsing_failures.append(parsing_failure)
			continue

		# the date is located in the first cell because of bad parsing
		if date := parse_date(df[0]):
			cur_date = date
		elif not cur_date:
			parsing_failure = _TableFailure(df_index, "date")
			_on_error(parsing_failure)
			parsing_failures.append(parsing_failure)
			continue

		# check if date has it's own row
		# this is a botch
		start_from = 1 if "\n" in df[0][0].strip() or not date else 2

		row_index: int
		row: Series
		for row_index, row in df.iloc[start_from:].iterrows():
			"""
			0: school class(es)
			1: lesson
			2: subject
			3: room
			4: teacher/stand-in
			5: message
			"""
			# parsing every cell in row except message
			parse_results = {
				"classes": _parse_classes(row[0]),
				"lesson": _parse_lesson(row[1]),
				"subject": _parse_replacement(row[2], always_from=True),
				"room": _parse_replacement(row[3], always_from=True),  # i am not sure about that. edge case?
				"teacher": _parse_replacement(row[4])
			}

			# checking for parsing failure
			try:
				for field, result in parse_results.items():
					if result is None:
						parsing_failure = _RowFailure(df_index, row_index, field, last_parsed)
						_on_error(parsing_failure)
						parsing_failures.append(parsing_failure)
						raise _SkipObject
			except _SkipObject:
				continue

			# defining vars
			classes = parse_results["classes"]
			lesson = parse_results["lesson"]
			subject_change_from, subject_change_to = parse_results["subject"]
			room_change_from, room_change_to = parse_results["room"]
			teacher_change_from, teacher_change_to = parse_results["teacher"]

			# getting action through parsing message
			# we sometimes have to guess because of human failure (message field is empty)
			guessed_action = False
			action = _parse_message(row[5])
			if action is None:
				action = _guess_action(teacher_change_from, teacher_change_to)
				guessed_action = True

				# botch: lately there are unreadable rows that don't imply any changes (for example 05.10.2021 TGD 18 7.)
				# I don't know what they are supposed to mean so we will skip them.
				if action == "room-change" and room_change_to is None:
					parsing_failure = _RowFailure(df_index, row_index, "unreadable", last_parsed)
					_on_error(parsing_failure)
					parsing_failures.append(parsing_failure)
					continue

			# botch: if a subject gets moved it gets set into subject_change_from
			# because of the "always_from=True". this needs to be corrected
			if subject_change_to is None and action == "replacement":
				subject_change_to = subject_change_from
				subject_change_from = None
			if room_change_to is None and action == "replacement":
				room_change_to = room_change_from
				room_change_from = None

			# change action "replacement" to "add" if subject_change_from empty
			# botch: checking teacher_change_from because sometimes both room and teacher changes
			if action == "replacement" and subject_change_from is None:
				if teacher_change_from is None:
					action = "add"
				else:
					subject_change_from = subject_change_to

			# creating response dict
			data_list.append({
				"classes": classes,
				"subject": {
					"from": subject_change_from,
					"to": subject_change_to
				},
				"room": {
					"from": room_change_from,
					"to": room_change_to
				},
				"teacher": {
					"from": teacher_change_from,
					"to": teacher_change_to
				},
				"date": cur_date,
				"lesson": lesson,
				"message": row[5].strip().replace("\n", ""),
				"action": action,
				"guessedAction": guessed_action,
			})

			# storing last parsed data_list
			last_parsed = data_list[-1]

	colorama.deinit()
	return {
		"failures": parsing_failures,
		"data": data_list
	}
