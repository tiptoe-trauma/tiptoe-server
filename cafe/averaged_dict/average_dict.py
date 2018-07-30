def fetch(key, dicts):
    return [d[key] for d in dicts]

def dict_typing(dicts):
    ret = {}
    for key in dicts[0].keys():
        ret[key] = type(dicts[0][key])

    for d in dicts[1:]:
        for key in d.keys():
            if type(d[key]) != ret[key]:
                if ret[key] == type(None):
                    ret[key] = type(d[key])
                elif type(d[key]) == type(None):
                    pass
                else:
                    raise Exception("Differing types for key - {}".format(key))
    return ret

def average_integer(numbers):
    return int(sum(numbers) / len(numbers))

def average_floats(numbers):
    return float(sum(numbers)) / float(len(numbers))

def average_bools(bools):
    num_conversion = []
    for b in bools:
        if b:
            num_conversion.append(1)
        else:
            num_conversion.append(0)
    return average_floats(num_conversion) >= .5

def count_strings(strings):
    counts = {}
    for s in strings:
        if s in counts.keys():
            counts[s] += 1
        else:
            counts[s] = 1
    counts = list(counts.items())
    return counts

def average_strings(strings):
    counts = count_strings(strings)
    counts.sort(key=lambda x: x[1], reverse=True)
    return counts[0][0]

def average_string_lists(lists):
    all_strings = []
    for slist in lists:
        for word in slist:
            all_strings.append(word)
    counts = count_strings(all_strings)
    common = map(lambda x: x[0], filter(lambda x: x[1] >= (len(lists) / 2.0), counts))
    return list(common)

def average_dict(input_dicts):
    ret = {}
    ret_types = dict_typing(input_dicts)
    for key in ret_types:
        if(ret_types[key] == type(1)):
            ret[key] = average_integer(fetch(key, input_dicts))
        elif(ret_types[key] == type(1.0)):
            ret[key] = average_floats(fetch(key, input_dicts))
        elif(ret_types[key] == type(True)):
            ret[key] = average_bools(fetch(key, input_dicts))
        elif(ret_types[key] == type('string')):
            ret[key] = average_strings(fetch(key, input_dicts))
        elif(ret_types[key] == type([])):
            ret[key] = average_string_lists(fetch(key, input_dicts))
        elif(ret_types[key] == type(None)):
            ret[key] = None
        else:
            raise Exception(
                    "{} type is not currently supported by average dict"
                    .format(ret_types[key]))
    return ret
