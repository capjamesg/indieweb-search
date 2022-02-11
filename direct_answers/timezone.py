from datetime import datetime

from pytz import timezone


def get_timezone(query):
    # time, timezone 1, timezone 2

    primary_time = [item for item in query.split() if ":" in item]

    minutes = "00"

    if primary_time:
        primary_time = primary_time[0]
        minutes = primary_time.split(":")[1].split(" ")[0]
    else:
        primary_time = None

    if primary_time is None:
        if "am" in query:
            position = query.find("am")
        elif "pm" in query:
            position = query.find("pm")

        primary_time = query[:position]

        primary_time = [char for char in primary_time if char.isdigit()]

        primary_time = "".join(primary_time).replace(" ", "")

        if len(primary_time) == 1:
            primary_time = "0" + primary_time + ":00"
        else:
            primary_time = primary_time + ":00"

    primary_timezone = "".join(query.split(" to ")[0].split()[-1:])

    secondary_timezone = "".join(query.split(" to ")[-1])

    timezone_reference_dict = {
        "uk": "GB",
        "et": "US/Eastern",
        "pt": "US/Pacific",
        "mt": "US/Mountain",
    }

    if timezone_reference_dict.get(primary_timezone):
        primary_timezone = timezone_reference_dict.get(primary_timezone, "")

    if timezone_reference_dict.get(secondary_timezone):
        secondary_timezone = timezone_reference_dict.get(secondary_timezone, "")

    visitor_timezone = timezone(primary_timezone)

    convert_to = timezone(secondary_timezone)

    if primary_time is not None:
        primary_time = datetime.strptime(primary_time, "%H:%M")

        visitor_timezone = visitor_timezone.localize(primary_time)

        visitor_timezone.replace(second=0)
    else:
        visitor_timezone = visitor_timezone.localize(datetime.now())

        visitor_timezone.replace(second=0)

    time_in_convert_to_timezone = visitor_timezone.astimezone(convert_to)

    final_time = time_in_convert_to_timezone.strftime("%H:%M")

    final_time = final_time.split(":")

    final_time[1] = minutes

    final_time = ":".join(final_time)

    if primary_time is not None:
        message = "{} ({}) in {} is {}.".format(
            primary_time.strftime("%H:%M"),
            primary_timezone,
            secondary_timezone,
            final_time,
        )
    else:
        message = f"The time in {secondary_timezone} is {final_time}."

    return message, {
        "type": "direct_answer",
        "breadcrumb": "https://indieweb-search.jamesg.blog",
        "title": "IndieWeb Search Direct Answer",
    }
