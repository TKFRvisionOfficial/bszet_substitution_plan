from typing import Iterable, Union, Tuple, List
from pandas import DataFrame, Series
import colorama
import re
from datetime import datetime


_MESSAGE_DICT = {
	"cancellation": ("Ausfall", "verschoben"),
	"replacement": ("statt", "Stundentausch", "vorgezogen"),
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
	if search_obj := re.search(r"\+(?P<to>[A-zÄ-ü\-_\s]+)\((?P<from>[A-zÄ-ü\-_\s]+)\)", to_parse):
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


def _parse_date(cell_0: str) -> Union[str, None]:
	if search_obj := re.search(r"\d\d\.\d\d\.\d\d\d\d", cell_0):
		return datetime.strptime(search_obj.group(0), "%d.%m.%Y").strftime("%Y-%m-%d")
	return None


def _parse_classes(class_cell: str) -> Union[List[str], None]:
	if len(search_results := re.findall(r"[A-z]+ ?\d+", class_cell.strip().replace("\n", ""))) > 0:
		return [search_result.replace(" ", "") for search_result in search_results]
	else:
		return None


def _parse_time(time_cell: str) -> Union[int, None]:
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
	elif teacher_change_to:  # very bitchy one. i am not sure. normally this would be room-change.
		return "cancellation"
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

	data_dict = {}
	cur_date = None
	last_parsed = None
	parsing_failures = []
	for df_index, df in enumerate(data_frames, start=1):
		# checking if table has proper size
		if len(df.columns) != 6:
			parsing_failure = _TableFailure(df_index, "amount of columns")
			_on_error(parsing_failure)
			parsing_failures.append(parsing_failure)
			continue

		# the date is located in the first cell because of bad parsing
		if date := _parse_date(df[0][0]):
			cur_date = date
		elif not cur_date:
			parsing_failure = _TableFailure(df_index, "date")
			_on_error(parsing_failure)
			parsing_failures.append(parsing_failure)
			continue

		row_index: int
		row: Series
		for row_index, row in df.iloc[1:].iterrows():
			"""
			0: school class(es)
			1: time
			2: subject
			3: room
			4: teacher/stand-in
			5: message
			"""
			# parsing every cell in row except message
			parse_results = {
				"classes": _parse_classes(row[0]),
				"time": _parse_time(row[1]),
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
			time = parse_results["time"]
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

			# adding result to data_dict
			if cur_date not in data_dict.keys():
				data_dict[cur_date] = {}
			for school_class in classes:
				if school_class not in data_dict[cur_date].keys():
					data_dict[cur_date][school_class] = {}
				data_dict[cur_date][school_class][time] = {
					"subject": {
						"from": subject_change_from,
						"to": subject_change_to
					},
					"room": {
						"from": room_change_from,
						"to": room_change_to
					},
					"action": action,
					"guessedAction": guessed_action
				}

			# saving parsed row for errors
			last_parsed = {**parse_results, "message": row[5]}

	colorama.deinit()
	return {
		"failures": parsing_failures,
		"data": data_dict
	}
