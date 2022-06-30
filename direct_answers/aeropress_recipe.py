import datetime
import random


def aeropress_recipe() -> dict:
    """
    Generate a random Aeropress recipe. This feature is an easter egg.

    :return: A dictionary containing randomly-generated Aeropress recipe variables.
    :rtype: dict
    """
    # Rounding helper function for timing

    def myround(x, base=5):
        result = base * round(x / base)
        if result == 10:
            result = 0
        return result

    # Generate brewing variables

    dose = random.randint(12, 16)

    # should dose have a .5 in it?
    dose_is_point_five = random.choice([True, False])

    # should the searcher use the inverted method?
    inverted = random.choice([True, False])

    # 1 in 7 chance I get a "really coarse" recipe with a coarse grind and a long brew time
    type_is_really_coarse = random.randint(1, 7)

    if type_is_really_coarse == 1:
        grind_size = random.randint(24, 30)
        time_in_seconds = random.randint(180, 300)
    else:
        grind_size = random.randint(18, 24)
        time_in_seconds = random.randint(45, 150)

    time_long = str(datetime.timedelta(seconds=time_in_seconds))
    time = time_long.split(":", 1)[1]

    last_time_int = time[-1]
    last_time_first_three = time[:-1]
    last_time_rounded = str(myround(int(last_time_int)))

    time = last_time_first_three + last_time_rounded

    filters = random.randint(1, 2)

    water = "250"

    stir_times = random.randint(0, 6)

    stirring_options = [
        "before putting the cap on",
        "before pluging",
        "both before putting the cap on and before plunging",
    ]

    stirring = random.choice(stirring_options)

    special_result = {
        "type": "aeropress_recipe",
        "dose": dose,
        "grind_size": grind_size,
        "time": time,
        "filters": filters,
        "water": water,
        "stirring": stirring,
        "stir_times": stir_times,
        "dose_is_point_five": dose_is_point_five,
        "inverted": inverted,
        "breadcrumb": "",
    }

    return special_result
