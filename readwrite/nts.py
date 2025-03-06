import re


def numbers_to_sinhala(sentence):
    output_list = []
    for word in sentence.split(" "):
        res = any(chr.isdigit() for chr in word)
        if res:
            pattern = r"([0-9.]+|[/.*+\-()]+|[a-zA-Z]+)"

            # Use re.split to split the input string based on the pattern
            result = re.split(pattern, word)

            # Remove empty strings from the result
            result = [s for s in result if s]
            for data in result:
                out = proccess(data)
                output_list.append(out)

        else:
            output_list.append(word)

    text = " ".join(output_list)
    return text


def proccess(word):
    if bool(re.match(r"^[0-9/\+\-\*\(\)\.]+$", word)):
        if word[0] == "0" or word[0] == "+":
            word = "එක"
        else:
            word = word.replace(".", "")
            word = word.replace("|", "")
            word = word.replace(",", "")
            if "/" in word:
                word = specialCharConvertion(word)
            else:
                word = normalConvertion(word)

    else:
        word = singleConvertion(word)

    return word


def add_letter_before_last(word, letter):
    if len(word) < 2:
        return word  # Return the word as is if it has only one letter
    return word[:-1] + word[-1] + letter


def specialCharConvertion(word):
    word_list = word.split("/")
    x = "කෙ"
    w1 = normalConvertion(word_list[0])
    w2 = normalConvertion(word_list[1])
    edited = add_letter_before_last(w2, x[1])
    word = edited + "න් " + w1

    return word


def singleConvertion(word):

    word = (
        word.replace("1", "එක ")
        .replace("2", "දෙක ")
        .replace("3", "තුන ")
        .replace("4", "හතර ")
        .replace("5", "පහ ")
        .replace("6", "හය ")
    )
    word = (
        word.replace("0", "බින්දුව ")
        .replace("7", "හත ")
        .replace("8", "අට ")
        .replace("9", "නමය ")
    )

    return word


def normalConvertion(word):
    splitss = {"/", ".", "*", "+", "-", "(", ")"}
    no_arr = []
    tem = ""
    for ch in word:
        if ch in splitss:
            no_arr.append(tem)
            no_arr.append(ch)
            tem = ""
        else:
            tem = tem + ch

    no_arr.append(tem)
    cno_arr = []
    for idx, num in enumerate(no_arr):
        if num.isdigit():
            if no_arr[idx - 1] == ".":
                last = num[-1]
                no_last = num[:-1]
                if last != "0":
                    last_text = number_to_words(int(last))
                else:
                    last_text = "බින්දුව"
            else:
                if num == "100":
                    cno_arr.append("සියය")
                if num == "1000":
                    cno_arr.append("දහස")
                elif num == "10000":
                    cno_arr.append("දසදහස")
                elif num == "100000":
                    cno_arr.append("ලක්ෂය")
                elif num == "1000000":
                    cno_arr.append("මිලියනය")
                elif num == "1000000000":
                    cno_arr.append("බිලියනය")
                else:
                    number = int(num)
                    n = number_to_words(number)
                    cno_arr.append(n)
        else:
            cno_arr.append(num)

    text = "".join(cno_arr)
    return text


def number_to_words(n):
    units = ["", "එක", "දෙක", "තුන", "හතර", "පහ", "හය", "හත", "අට", "නමය"]
    unitsx = ["", "එක", "දෙ", "තුන්", "හාර", "පන්", "හය", "හත්", "අට", "නම"]
    teens = [
        "දහය",
        "එකොළහ",
        "දොළහ",
        "දහතුන",
        "දාහතර",
        "පහළොව",
        "දාසය",
        "දාහත",
        "දහඅට",
        "දහනමය",
    ]
    teensx = [
        "දහ",
        "එකොළොස්",
        "දොළොස්",
        "දහතුන්",
        "දාහතර",
        "පහළොස්",
        "දාසය",
        "දාහත්",
        "දහඅට",
        "දහනම",
    ]
    tens = ["", "දහය", "විස්ස", "තිහ", "හතළිහ", "පනහ", "හැට", "හැත්තෑව", "අසූව", "අනූව"]
    tensx = ["", "", "විසි", "තිස්‌", "හතලිස්", "පනස්", "හැට", "හැත්තෑ", "අසූ", "අනූ"]
    thousands = ["", "දහස්", "මිලියන", "බිලියන"]

    def helper(num, moreThanThousand):
        if num == 0:
            return []
        elif num < 10:
            if moreThanThousand:
                return [unitsx[num]]
            else:
                return [units[num]]
        elif num < 20:
            if moreThanThousand:
                return [teensx[num - 10]]
            else:
                return [teens[num - 10]]
        elif num < 100:
            if num % 10 == 0:
                return [tens[num // 10]] + helper(num % 10, moreThanThousand)
            else:
                return [tensx[num // 10]] + helper(num % 10, moreThanThousand)
        elif num < 1000:
            if num % 10 == 0:
                return (
                    [unitsx[num // 100]] + ["සිය"] + helper(num % 100, moreThanThousand)
                )
            else:
                return (
                    [unitsx[num // 100]] + ["සිය"] + helper(num % 100, moreThanThousand)
                )
        else:
            return helper(num // 1000) + ["දහස්"] + helper(num % 1000, moreThanThousand)

    words = []
    idx = 0
    while n > 0:
        if idx > 0:
            words = helper(n % 1000, True) + [thousands[idx]] + words
        else:
            words = helper(n % 1000, False) + [thousands[idx]] + words
        n //= 1000
        idx += 1

    rt = "".join(words)
    frt = rt.replace("  ", " ")
    return frt
