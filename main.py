import robin_stocks.robinhood as r
import numpy as np
import datetime as d
import math
import yahoo_fin.options as ops
import yahoo_fin.stock_info as y
from dateutil.relativedelta import relativedelta


# sign in to account with input
password = input('Type password for Robinhood account here: ')
r.login(USERNAME, password)
print("Bot has began!")


def next_friday():  # Returns date of upcoming Friday in form YYYY-MM-DD
    date = d.date.today()
    friday = date + d.timedelta((4 - date.weekday()) % 7)
    if date == friday:
        friday = friday + d.timedelta(7)

    return friday


def weekly_change(ticker):  # Calculates weekly % change of a given stock for the past 5 years. Returns a list of %s
    startDate = d.date.today() - relativedelta(years=5)
    today = d.date.today()
    endDate = today.strftime("%d/%m/%y")
    hist_data = y.get_data(ticker="AAPL", start_date=startDate, end_date=endDate, interval='1wk')
    hist_data = hist_data.loc[:, ['open', 'close']]
    hist_data['Percent Change'] = ((hist_data['close'] - hist_data['open']) / hist_data['open']) * 100
    percentChange = list(hist_data['Percent Change'])
    print(percentChange)
    return percentChange


def get_success_rate(liveprice, callOptionsData, weeklyChange):
    # Returns list of % of time stock historically finishes above 8 analyzed strike prices
    strikePrices = callOptionsData["Strike"].to_list()

    percentDiff = np.zeros(len(strikePrices))
    for i in range(len(strikePrices)):
        percentDiff[i] = ((strikePrices[i] - liveprice) / liveprice) * 100

    successRate = np.zeros(len(percentDiff))
    for i in range(len(percentDiff)):
        successCount = 0
        for j in range(len(weeklyChange)):
            if percentDiff[i] <= weeklyChange[j]:
                successCount += 1
        successRate[i] = (successCount / len(weeklyChange))
    return successRate


def get_currnet_price(ticker):
    livePrice = y.get_live_price(ticker)                                                                    # gathers live price from yahoo
    return livePrice


def call_options_data(ticker, friday, livePrice):
    optionsCalls = ops.get_calls(ticker, friday)                                                            # requests information to create main dataframe
    indexOptions = optionsCalls.index                                                                       # indexes the options dataframe
    condition = optionsCalls["Strike"] == round(livePrice)                                                  # looks through the strike prices column for the current price and makes a dataframe of True and False values
    strikePricesIndex = indexOptions[condition]                                                             # saves the true indexes and store it as a Int64Index
    strikePricesIndex_tolist = strikePricesIndex.tolist()                                                   # converts the index to a list for arithmatic purposes
    newOptionsCalls = optionsCalls.loc[(strikePricesIndex_tolist[0] - 4):
                                       (strikePricesIndex_tolist[0] + 3), ["Strike", "Last Price"]]         # creates new dataframe with correct strike prices and call options prices
    return newOptionsCalls                                                                                  #return dataframe of StikePrices and cost of calls


def put_options_data(ticker, friday, livePrice):
    optionsPuts = ops.get_puts(ticker, friday)                                                              # requests information to create main dataframe
    indexOptions = optionsPuts.index                                                                        # indexes the options dataframe
    condition = optionsPuts["Strike"] == round(livePrice)                                                   # looks through the strike prices column for the current price and makes a dataframe of True and False values
    strikePricesIndex = indexOptions[condition]                                                             # saves the true indexes and store it as a Int64Index
    strikePricesIndex_tolist = strikePricesIndex.tolist()                                                   # converts the index to a list for arithmatic purposes
    newOptionsPuts = optionsPuts.loc[(strikePricesIndex_tolist[0] - 4):
                                     (strikePricesIndex_tolist[0] + 3), ["Strike", "Last Price"]]           # creates new dataframe with correct strike prices and call options prices
    return newOptionsPuts                                                                                   #returns dataframe of StrikePrices and cost of puts


def call_debit_analysis(callOptionsData, successRate2):
    strikePrices = callOptionsData["Strike"].to_list()
    costsCalls = callOptionsData["Last Price"].to_list()

    strikePricesLow = strikePrices[:len(costsCalls) // 2]
    statisticalEarnings = np.zeros(len(strikePricesLow) - 1)

    for i in range(len(statisticalEarnings)):
        risk = costsCalls[i] - costsCalls[i + 1]
        reward = (strikePrices[i + 1] - strikePrices[i]) - risk
        statisticalEarnings[i] = (successRate2[i + 1] * reward) - ((1 - successRate2[i + 1]) * risk)
    bestOptionIndexTuple = np.where(statisticalEarnings == max(statisticalEarnings))
    bestOptionIndexArray = bestOptionIndexTuple[0]
    bestOptionIndex = bestOptionIndexArray[0]
    limitPrice = abs(costsCalls[bestOptionIndex] - costsCalls[bestOptionIndex + 1]) + .02
    buyCallSellCall = [strikePricesLow[bestOptionIndex], strikePricesLow[bestOptionIndex + 1],
                       max(statisticalEarnings), round(limitPrice, 2)]
    return buyCallSellCall


def put_credit_analysis(putOptionsData, successRate2):
    strikePrices = putOptionsData["Strike"].to_list()
    costsPuts = putOptionsData["Last Price"].to_list()

    strikePricesLow = strikePrices[:len(costsPuts) // 2]
    statisticalEarnings = np.zeros(len(strikePricesLow) - 1)

    for i in range(len(statisticalEarnings)):
        reward = costsPuts[i + 1] - costsPuts[i]
        risk = (strikePrices[i + 1] - strikePrices[i]) - reward
        statisticalEarnings[i] = (successRate2[i + 1] * reward) - ((1 - successRate2[i + 1]) * risk)

    bestOptionIndexTuple = np.where(statisticalEarnings == max(statisticalEarnings))
    bestOptionIndexArray = bestOptionIndexTuple[0]
    bestOptionIndex = bestOptionIndexArray[0]
    limitPrice = abs(costsPuts[bestOptionIndex + 1] - costsPuts[bestOptionIndex]) + .02
    buyPutSellPut = [strikePricesLow[bestOptionIndex], strikePricesLow[bestOptionIndex + 1],
                     max(statisticalEarnings), round(limitPrice, 2)]
    return buyPutSellPut


def call_credit_analysis(callOptionsData, successRate2):
    strikePrices = callOptionsData["Strike"].to_list()
    costsCalls = callOptionsData["Last Price"].to_list()

    strikePricesHigh = strikePrices[len(costsCalls) // 2:]
    costsCallsHigh = costsCalls[len(costsCalls) // 2:]
    statisticalEarnings = np.zeros(len(strikePricesHigh) - 1)
    successRate2 = successRate2[len(costsCalls) // 2:]

    for i in range(len(successRate2)):
        successRate2[i] = 1 - successRate2[i]

    for i in range(len(statisticalEarnings)):
        reward = costsCallsHigh[i] - costsCallsHigh[i + 1]
        risk = (strikePrices[i + 1] - strikePrices[i]) - reward
        statisticalEarnings[i] = (successRate2[i] * reward) - ((1 - successRate2[i]) * risk)

    bestOptionIndexTuple = np.where(statisticalEarnings == max(statisticalEarnings))
    bestOptionIndexArray = bestOptionIndexTuple[0]
    bestOptionIndex = bestOptionIndexArray[0]
    limitPrice = abs(costsCallsHigh[bestOptionIndex] - costsCallsHigh[bestOptionIndex + 1]) + .02
    buyCallSellCall = [strikePricesHigh[bestOptionIndex + 1], strikePricesHigh[bestOptionIndex],
                       max(statisticalEarnings), round(limitPrice, 2)]

    return buyCallSellCall


def put_debit_analysis(putOptionsData, successRate2):
    strikePrices = putOptionsData["Strike"].to_list()
    costsPuts = putOptionsData["Last Price"].to_list()

    strikePricesHigh = strikePrices[len(costsPuts) // 2:]
    costsPutsHigh = costsPuts[len(costsPuts) // 2:]
    successRate2 = successRate2[len(successRate2) // 2:]

    statisticalEarnings = np.zeros(len(strikePricesHigh) - 1)

    for i in range(len(successRate2)):
        successRate2[i] = 1 - successRate2[i]

    for i in range(len(statisticalEarnings)):
        risk = costsPutsHigh[i + 1] - costsPutsHigh[i]
        reward = (strikePrices[i + 1] - strikePrices[i]) - risk
        statisticalEarnings[i] = (successRate2[i] * reward) - ((1 - successRate2[i]) * risk)

    bestOptionIndexTuple = np.where(statisticalEarnings == max(statisticalEarnings))
    bestOptionIndexArray = bestOptionIndexTuple[0]
    bestOptionIndex = bestOptionIndexArray[0]
    limitPrice = abs(costsPuts[bestOptionIndex + 1] - costsPuts[bestOptionIndex]) + .02
    buyPuttSellPutt = [strikePricesHigh[bestOptionIndex + 1], strikePricesHigh[bestOptionIndex],
                       max(statisticalEarnings), round(limitPrice, 2)]

    return buyPuttSellPutt


def account_verification():
    profile = r.profiles.load_account_profile(info='account_number')

    if profile == '822946174':
        confirm = input('You are logged into Robinhood as Zachary Loschinskey; \n Would you like to continue? (Y/N): ')
    elif profile == '856834254':
        confirm = input('You are logged into Robinhood as Jacob Loschinskey; \n Would you like to continue? (Y/N): ')
    else:
        confirm = input('You are logging into an unrecognized account; \n Would you like to continue? (Y/N): ')

    if str(confirm.upper()) == 'Y':
        loopVar = 0
    else:
        loopVar = 1
    return loopVar


#Finding account balance
# accBalance = r.profiles.load_account_profile(info='portfolio_cash')
# print(accBalance)
# a = account_verification()


a = 0
while a == 0:  # main loop
    print('loop entered')
    tickerArray = ['AAPL']

    count = 0
    for i in range(len(tickerArray)):

        tickerInput = tickerArray[i]

        # Check available balance ******We do not necessarily need this********* JL
        #accBalance = r.profiles.load_account_profile(info='portfolio_cash')

        # Functions to Variables
        friday = next_friday()
        strFriday = str(next_friday())
        weeklyChange = weekly_change(tickerInput)
        currentPrice = get_currnet_price(tickerInput)
        callOptionsData = call_options_data(tickerInput, friday, currentPrice)
        putOptionsData = put_options_data(tickerInput, friday, currentPrice)
        successRate = get_success_rate(currentPrice, callOptionsData, weeklyChange)
        roundedCurrentPrice = math.ceil(currentPrice)

        # ANALYZE CALL DEBIT SPREAD
        callDebit = call_debit_analysis(callOptionsData, successRate)

        # ANALYZE PUT CREDIT SPREAD
        putCredit = put_credit_analysis(putOptionsData, successRate)

        # ANALYZE CALL CREDIT SPREAD
        callCredit = call_credit_analysis(callOptionsData, successRate)

        # ANALYZE PUT DEBIT SPREAD
        putDebit = put_debit_analysis(putOptionsData, successRate)

        if (count % 2) == 0:
            if callDebit[2] >= putCredit[2] and callDebit[2] > 0 and callDebit[2] >= .02:
                # BU
                leg1 = {"expirationDate": strFriday, "strike": callDebit[0],
                        "optionType": "call", "effect": "open", "action": "buy"}
                leg2 = {"expirationDate": strFriday, "strike": callDebit[1],
                        "optionType": "call", "effect": "open", "action": "sell"}
                spread = [leg1, leg2]

                #order = r.order_option_spread("debit", callDebit[3], tickerInput, 1, spread)
                #print(order)
                count += 1
                print('Call Debit Bought')

            elif putCredit[2] > callDebit[2] and putCredit[2] > 0 and putCredit[2] >= .02:
                # BUY PUT CREDIT
                leg1 = {"expirationDate": strFriday, "strike": putCredit[0],
                        "optionType": "put", "effect": "open", "action": "buy"}
                leg2 = {"expirationDate": strFriday, "strike": putCredit[1],
                        "optionType": "put", "effect": "open", "action": "sell"}
                spread = [leg1, leg2]

                #order = r.order_option_spread("credit", putCredit[3], tickerInput, 1, spread)
                #print(order)
                count += 1
                print('Put Credit Bought')

            else:
                print('This stock (' + tickerInput + ') is not bussin :(')

        else:
            if putDebit[2] >= callCredit[2] and putDebit[2] > 0 and putDebit[2] >= .02:
                # BUY PUT DEBIT
                leg1 = {"expirationDate": strFriday, "strike": putDebit[0],
                        "optionType": "put", "effect": "open", "action": "buy"}
                leg2 = {"expirationDate": strFriday, "strike": putDebit[1],
                        "optionType": "put", "effect": "open", "action": "sell"}
                spread = [leg1, leg2]

                #order = r.order_option_spread("debit", putDebit[3], tickerInput, 1, spread)
                #print(order)
                count += 1
                print('Put Debit Bought')

            elif putDebit[2] < callCredit[2] and callCredit[2] > 0 and callCredit[2] >= .02:
                # BUY CALL CREDIT
                leg1 = {"expirationDate": strFriday, "strike": callCredit[0],
                        "optionType": "call", "effect": "open", "action": "buy"}
                leg2 = {"expirationDate": strFriday, "strike": callCredit[1],
                        "optionType": "call", "effect": "open", "action": "sell"}
                spread = [leg1, leg2]

                #order = r.order_option_spread("credit", callCredit[3], tickerInput, 1, spread)
                #print(order)
                count += 1
                print('Call Credit Bought')

            else:
                print('This stock (' + tickerInput + ') is not bussin :(')
    a = 1

# r.export_completed_option_orders("../")
