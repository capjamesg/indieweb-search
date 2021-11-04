import datetime
import re

def parse_advanced_search(advanced_filter_to_search, query_with_handled_spaces, query_values_in_list):
	# Advanced search term to look for (i.e. before:")
	look_for = query_with_handled_spaces.find(advanced_filter_to_search)
	if look_for != -1:
		# Find value that I'm looking for (date, category, etc.)
		get_value = re.findall(r'{}([^"]*)"'.format(advanced_filter_to_search), query_with_handled_spaces)

		if advanced_filter_to_search == "site:":
			get_value[0] = get_value[0].replace("https://", "").replace("http://", "").split("/")[0]
			
		query_with_handled_spaces = query_with_handled_spaces.replace('{}{}"'.format(advanced_filter_to_search, get_value[0]), "")

		# Format date as string if user provides before: or after: value then append date to list of query values
		# Otherwise append value to list of query values

		if "before" in advanced_filter_to_search or "after" in advanced_filter_to_search:
			query_values_in_list.append(datetime.datetime.strptime(get_value[0], "%Y-%d-%m"))
		else:
			query_values_in_list.append(get_value[0].replace('"', ""))

	return query_values_in_list, query_with_handled_spaces

# Process category search and defer dates to parse_advanced_search function
def handle_advanced_search(query_with_handled_spaces):
	query_values_in_list = []
	
	query_values_in_list, query_with_handled_spaces = parse_advanced_search('before:"', query_with_handled_spaces, query_values_in_list)
	query_values_in_list, query_with_handled_spaces = parse_advanced_search('after:"', query_with_handled_spaces, query_values_in_list)
	query_values_in_list, query_with_handled_spaces = parse_advanced_search('js:"', query_with_handled_spaces, query_values_in_list)

	if 'inurl:"' in query_with_handled_spaces:
		value_to_add = "%" + re.findall(r'{}([^"]*)"'.format('inurl:"'), query_with_handled_spaces)[0] + "%"
		query_values_in_list.append(value_to_add)
		query_with_handled_spaces = query_with_handled_spaces.replace('{}{}"'.format('inurl:"', re.findall(r'{}([^"]*)"'.format('inurl:"'), query_with_handled_spaces)[0]), "")

	if "site:" in query_with_handled_spaces:
		value_to_add = "%" + re.findall(r'{}([^"]*)"'.format('site:"'), query_with_handled_spaces)[0] + "%"
		query_values_in_list.append(value_to_add)
		query_with_handled_spaces = query_with_handled_spaces.replace('{}{}"'.format('site:"', re.findall(r'{}([^"]*)"'.format('site:"'), query_with_handled_spaces)[0]), "")
	
	return query_values_in_list, query_with_handled_spaces