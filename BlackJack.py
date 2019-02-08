import sys
import os
from random import shuffle
import matplotlib.pyplot as plt
import pandas as pd

#NOT CURRENTLY USED
#import numpy as np
#import scipy.stats as stats
#import pylab as pl

#from importer.StrategyImporter import StrategyImporter
import csv #for csv.DictReader

class StrategyImporter(object):
    """
    """
    hard_strategy = {}
    soft_strategy = {}
    pair_strategy = {}
    dealer_strategy = {}

    def __init__(self, player_file):
        self.player_file = "BasicStrategy.csv"
        #self.player_file = "BadStrategy.csv" #AROUND -0.5 EDGE - REMOVED SOME OF THE DOUBLING/SPLITTING/SURRENDERING

    #TODO: Revalue these to match the lines in the CSV file without odd counting
    def import_player_strategy(self):
        hard = 21 #21 - 17 lines
        soft = 21 #21 - 10 lines
        pair = 20 #20 - 9 lines

        with open(self.player_file, 'r') as player_csv:
            reader = csv.DictReader(player_csv, delimiter = ';')
            for row in reader:
                if hard >= 5: #5 get to 1
                    self.hard_strategy[hard] = row
                    hard -= 1  # Subtract 1
                elif soft >= 12: #12 - Get to 1
                    self.soft_strategy[soft] = row
                    soft -= 1 #subtract 1
                elif pair >= 4: #4 #gets to one
                    self.pair_strategy[pair] = row
                    pair -= 2 #-2: Subtract 1

        return self.hard_strategy, self.soft_strategy, self.pair_strategy      
#END IMPORTER

scriptDirectory = os.path.dirname(os.path.realpath(__file__))

NUM_HANDS = 5000000
#NUM_GAMES = 1000 #118203 average 43 hands per game (deck_size * shoe_size * shoe_penetration) with 75% penetration (.25), 23,500 games is 1m hands.
SHOE_PENETRATION = 0.25 # reshuffle after 75% (minus 1.0 from the set number) of all cards are played

#CARD COUNTING - TOP VALUES (WHEN COUNT IS VERY HIGH)
TRUE_COUNT_TOP = 1 #3 Institute BET_SPREAD if true count >= this number - default was 6
TOP_BET_SPREAD = 1.0 #4 Bet n-times (if set to 20.0, 20-times) the money if the count is player-favorable
#CARD COUNTING - MID VALUES (WHEN COUNT IS HIGH)
TRUE_COUNT_MID = 1 #1 Institute BET_SPREAD if true count >= this number - default was 6
MID_BET_SPREAD = 1.0 #2 Bet n-times (if set to 20.0, 20-times) the money if the count is player-favorable
#STANDARD SIZE OF BET
SIZE_OF_BET = 100.0 #size of the bet, can be any integer, is multiplied by bet_spread

#CASINO RULES
SHOE_SIZE = 6
BLACKJACK_PAYOUT = 1.5 #blackjack payout is 1.5 (3:2) or 1.2 (6:5)
DEALER_HITS_SOFT = True #True if dealer should hit soft 17, or False if dealer should stand
#MAX_SPLIT = 4 # max hands to split

BLACKJACK_RULES = {
    'triple7': False,  # Count 3x7 as a blackjack
}

DECK_SIZE = 52.0

CARDS = {
    "Ace": 11, "Two": 2, "Three": 3, "Four": 4, "Five": 5, "Six": 6,
    "Seven": 7, "Eight": 8, "Nine": 9, "Ten": 10, "Jack": 10, "Queen": 10,
    "King": 10
    }

'''
COUNTING STRATEGIES
'''
NO_STRATEGY = {
    "Ace": 0, "Two": 0, "Three": 0, "Four": 0, "Five": 0, "Six": 0, "Seven": 0,
    "Eight": 0, "Nine": 0, "Ten": 0, "Jack": 0, "Queen": 0, "King": 0
    }

HI_LO_STRATEGY = {
    "Ace": -1, "Two": 1, "Three": 1, "Four": 1, "Five": 1, "Six": 1, "Seven": 0,
    "Eight": 0, "Nine": 0, "Ten": -1, "Jack": -1, "Queen": -1, "King": -1
    }

BASIC_OMEGA_II = {
    "Ace": 0, "Two": 1, "Three": 1, "Four": 2, "Five": 2, "Six": 2, "Seven": 1,
    "Eight": 0, "Nine": -1, "Ten": -2, "Jack": -2, "Queen": -2, "King": -2
    }

#SELECT WHICH COUNTING STRATEGY (HI_LO_STRATEGY  - BASIC_OMEGA_II)
COUNTING_STRATEGY = HI_LO_STRATEGY


HARD_STRATEGY = {}
SOFT_STRATEGY = {}
PAIR_STRATEGY = {}


class Card(object):
    """
    Represents a playing card with name and value.
    """
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return "%s" % self.name

    @property
    def count(self):
        return COUNTING_STRATEGY[self.name]


class Shoe(object):
    """
    Represents the shoe, which consists of a number of card decks.
    """
    reshuffle = False

    def __init__(self, decks):
        self.count = 0
        self.count_history = []
        self.ideal_count = {}
        self.decks = decks
        self.cards = self.init_cards()
        self.init_count()

    def __str__(self):
        s = ""
        for c in self.cards:
            s += "%s\n" % c
        return s

    def init_cards(self):
        """
        Initialize the shoe with shuffled playing cards and set count to zero.
        """
        self.count = 0
        self.count_history.append(self.count)

        cards = []
        for d in range(self.decks):
            for c in CARDS:
                for i in range(0, 4):
                    cards.append(Card(c, CARDS[c]))
        shuffle(cards)
        return cards

    def init_count(self):
        """
        Keep track of the number of occurrences for each card in the shoe in
        the course over the game. ideal_count is a dictionary containing (card
        name - number of occurrences in shoe) pairs
        """
        for card in CARDS:
            self.ideal_count[card] = 4 * SHOE_SIZE

    def deal(self):
        """
        Returns:    The next card off the shoe. If the shoe penetration is 
                    reached, the shoe gets reshuffled.
        """
        if self.shoe_penetration() < SHOE_PENETRATION:
            self.reshuffle = True
        card = self.cards.pop()

        assert self.ideal_count[card.name] > 0, "Either a cheater or a bug!"
        self.ideal_count[card.name] -= 1

        self.do_count(card)
        return card

    def do_count(self, card):
        """
        Add the dealt card to current count.
        """
        self.count += COUNTING_STRATEGY[card.name]
        self.count_history.append(self.truecount())

    def truecount(self):
        """
        Returns: The current true count.
        """
        return self.count / (self.decks * self.shoe_penetration())

    def regcount(self):
        """
        Returns: The current count.
        """
        return self.count

    def shoe_penetration(self):
        """
        Returns: Ratio of cards that are still in the shoe to all initial
                 cards.
        """
        return len(self.cards) / (DECK_SIZE * self.decks)


class Hand(object):
    """
    Represents a hand, either from the dealer or from the player
    """
    _value = 0
    _aces = []
    _aces_soft = 0
    splithand = False
    surrender = False
    doubled = False

    def __init__(self, cards):
        self.cards = cards

    def __str__(self):
        h = ""
        for c in self.cards:
            h += "%s[%s] " % (c, c.count)
        return h

    @property
    def value(self):
        """
        Returns: The current value of the hand (aces are either counted as 1 or
        11).
        """
        self._value = 0
        for c in self.cards:
            self._value += c.value
        
        #if busted but have an ace, revalue from 11 to 1
        if self._value > 21 and self.aces_soft > 0:
            for ace in self.aces:
                if ace.value == 11:
                    self._value -= 10
                    ace.value = 1
                    if self._value <= 21:
                        break

        return self._value

    @property
    def aces(self):
        """
        Returns: The all aces in the current hand.
        """
        self._aces = []
        for c in self.cards:
            if c.name == "Ace":
                self._aces.append(c)
        return self._aces

    @property
    def aces_soft(self):
        """
        Returns: The number of aces valued as 11
        """
        self._aces_soft = 0
        for ace in self.aces:
            if ace.value == 11:
                self._aces_soft += 1
        return self._aces_soft

    def soft(self):
        """
        Determines whether the current hand is soft (soft means that it
        consists of aces valued at 11).
        """
        if self.aces_soft > 0:
            return True
        else:
            return False

    def splitable(self):
        """
        Determines if the current hand can be split.
        """
        #MAX_SPLIT TO LIMIT HOW MANY TIMES TO SPLIT. CAUSES ERROR SINCE HARD STRATEGY SAYS TO SPLIT. NEED AN IF/ELSE FOR STRATEGY (l432)
        #if self.length() == 2 and self.cards[0].name == self.cards[1].name and len(game.player.hands) <= MAX_SPLIT:
        if self.length() == 2 and self.cards[0].name == self.cards[1].name:
            return True
        else:
            return False

    def blackjack(self):
        """
        Check a hand for a blackjack, taking the defined BLACKJACK_RULES into
        account.
        """
        if not self.splithand and self.value == 21:
            if (all(c.value == 7 for c in self.cards) and BLACKJACK_RULES['triple7']):
                return True
            elif self.length() == 2:
                return True
            else:
                return False
        else:
            return False

    def busted(self):
        """
        Checks if the hand is busted.
        """
        if self.value > 21:
            return True
        else:
            return False

    def add_card(self, card):
        """
        Add a card to the current hand.
        """
        self.cards.append(card)

    def split(self):
        """
        Split the current hand.
        Returns: The new hand created from the split.
        """
        self.splithand = True
        c = self.cards.pop()
        new_hand = Hand([c])
        new_hand.splithand = True
        return new_hand

    def length(self):
        """
        Returns: The number of cards in the current hand.
        """
        return len(self.cards)


class Log(object):
    """
    Represents a history of hands and associated actions.
    """
    def __init__(self):
        try:
            self.hands = pd.read_pickle(scriptDirectory+'/player_history')
        except FileNotFoundError:
            self.hands = None

    def __str__(self):
        print(self.hands)

    def add_hand(self, action, hand, dealer_hand, shoe):
        d = {'hand': [hand.value], 'soft': [hand.soft()],
             'splitable': [hand.splitable()],
             'dealer': [dealer_hand.cards[0].value],
             'truecount': [shoe.truecount()], 'action': [action.upper()]
             }
        if self.hands is None:
            self.hands = pd.DataFrame(data=d)
        else:
            self.hands = self.hands.append(pd.DataFrame(data=d))

    def save(self):
        self.hands.to_pickle(scriptDirectory+'/player_history')


class Player(object):
    """
    Represent a player
    """
    def __init__(self, hand=None, dealer_hand=None):
        self.hands = [hand]
        self.dealer_hand = dealer_hand
        self.autoplay = True
        self.history = Log()

    def set_hands(self, new_hand, new_dealer_hand):
        self.hands = [new_hand]
        self.dealer_hand = new_dealer_hand

    def play(self, shoe):
        for hand in self.hands:
            print("PLAYING HAND: %s" % hand)
            self.play_hand(hand, shoe)
    def play_hand(self, hand, shoe):
        if hand.length() < 2:
            if hand.cards[0].name == "Ace":
                hand.cards[0].value = 11
            self.hit(hand, shoe)

        #while not hand.busted() and not hand.blackjack():            
        while not hand.busted() and not hand.blackjack() and not self.dealer_hand.blackjack():          
            if self.autoplay:
                if hand.soft():
                    flag = SOFT_STRATEGY[hand.value][
                        self.dealer_hand.cards[0].name]
                    print("SOFT STRATEGY (d:", self.dealer_hand.cards[0].name, "| p:", hand.value, ")")
                elif hand.splitable():
                    flag = PAIR_STRATEGY[hand.value][
                        self.dealer_hand.cards[0].name]
                    print("PAIR STRATEGY (d:", self.dealer_hand.cards[0].name, "| p:", hand.value, ")")
                else:
                    flag = HARD_STRATEGY[hand.value][
                        self.dealer_hand.cards[0].name]
                    print("HARD STRATEGY (d:", self.dealer_hand.cards[0].name, "| p:", hand.value, ")")
            else:
                print("DEALER HAND: %s (%d)" % (self.dealer_hand, self.dealer_hand.value))
                print("PLAYER HAND: %s (%d)" % (self.hands[0], self.hands[0].value))
                print("Count=%s, Penetration=%s\n" %
                      ("{0:.2f}".format(shoe.count),
                       "{0:.2f}".format(shoe.shoe_penetration())))
                flag = input("Action (H=Hit, S=Stand, D=Double, P=Split, "
                             "Sr=Surrender, Q=Quit): ")
                if flag != 'Q':
                    self.history.add_hand(flag, hand, self.dealer_hand, shoe)

            if flag.upper() == 'D':
                if hand.length() == 2:
                    print("DOUBLE DOWN")
                    hand.doubled = True
                    self.hit(hand, shoe)
                    break
                else:
                    flag = 'H'

            if flag.upper() == 'SR':
                if hand.length() == 2:
                    print("SURRENDER")
                    hand.surrender = True
                    break
                else:
                    flag = 'H'

            if flag.upper() == 'H':
                self.hit(hand, shoe)

            if flag.upper() == 'P':
                self.split(hand, shoe)

            if flag.upper() == 'S':
                break

            if flag.upper() == 'Q':
                exit()

    def hit(self, hand, shoe):
        c = shoe.deal()
        hand.add_card(c)
        ##print("PLAYER HIT: %s (%s - %s)" % (c, hand, hand.value))
        print("PLAYER HIT: %s (%s)" % (c, hand.value))

    def split(self, hand, shoe):
        self.hands.append(hand.split())
        print("SPLIT %s" % hand)
        self.play_hand(hand, shoe)


class Dealer(object):
    """
    Represent the dealer
    """
    def __init__(self, hand=None):
        self.hand = hand

    def set_hand(self, new_hand):
        self.hand = new_hand

    #TODO: Adjust this if we want to change dealer hitting on SOFT 17
    def play(self, shoe):
        #Rule to adjust soft or hard
        if DEALER_HITS_SOFT == True:
            #if soft ace and over 17
            if self.hand.aces_soft > 0:
                while self.hand.aces_soft > 0 and self.hand.value <= 17:
                    print("DEALER HITTING SOFT ACE!")
                    self.hit(shoe)
            #no soft aces
            while self.hand.value < 17:
                self.hit(shoe)
        else:
            while self.hand.value < 17:
                self.hit(shoe)


    def hit(self, shoe):
        c = shoe.deal()
        self.hand.add_card(c)
        #print("DEALER HIT: %s (%s - %s)" % (c, self.hand, self.hand.value))
        print("DEALER HIT: %s (%s)" % (c, self.hand.value))

    # Returns an array of 6 numbers representing the probability that the final
    # score of the dealer is
    # [17, 18, 19, 20, 21, Busted] '''
    # TODO Differentiate 21 and BJ
    # TODO make an actual tree, this is false AF
    #def get_probabilities(self):
        #start_value = self.hand.value
        # We'll draw 5 cards no matter what an count how often we got 17, 18,
        # 19, 20, 21, Busted


class Tree(object):
    """
    A tree that opens with a statistical card and changes as a new
    statistical card is added. In this context, a statistical card is a list of possible values, each with a probability.
    e.g : [2 : 0.05, 3 : 0.1, ..., 22 : 0.1]
    Any value above 21 will be truncated to 22, which means 'Busted'.
    """
    #TODO to test
    def __init__(self, start=[]):
        self.tree = []
        self.tree.append(start)

    def add_a_statistical_card(self, stat_card):
        # New set of leaves in the tree
        leaves = []
        for p in self.tree[-1]:
            for v in stat_card:
                new_value = v + p
                proba = self.tree[-1][p] * stat_card[v]
                if (new_value > 21):
                    # All busted values are 22
                    new_value = 22
                if (new_value in leaves):
                    leaves[new_value] = leaves[new_value] + proba
                else:
                    leaves[new_value] = proba


class Game(object):
    """
    A sequence of Blackjack Rounds that keeps track of total money won or lost
    """
    def __init__(self):
        self.shoe = Shoe(SHOE_SIZE)
        self.money = 0.0
        self.bet = 0.0
        self.stake = SIZE_OF_BET
        self.player = Player()
        self.dealer = Dealer()
        self.status = ""
        self.win = 0.0


    def get_hand_winnings(self, hand):
        win = 0.0
        bet = self.stake
        status_info = ""
        if not hand.surrender:
            if hand.busted():
                status = "LOST"
            else:
                if self.dealer.hand.blackjack(): #Need to check to see if dealer has blackjack
                    if hand.blackjack():
                        status = "PUSH"
                        status_info = "DEALER AND PLAYER BOTH HAVE BLACKJACK!"
                    else:
                        status = "LOST" #automatic lost due to dealer blackjack
                        status_info = "DEALER HAS BLACKJACK!"
                elif hand.blackjack(): #Need to check to see if player has blackjack
                    if self.dealer.hand.blackjack():
                        status = "PUSH"
                        status_info = "DEALER AND PLAYER BOTH HAVE BLACKJACK!"
                    else:
                        status = "WON BLACKJACK"
                        status_info = "PLAYER HAS BLACKJACK!"
                elif self.dealer.hand.busted():
                    status = "WON"
                elif self.dealer.hand.value < hand.value:
                    status = "WON"
                elif self.dealer.hand.value > hand.value:
                    status = "LOST"
                elif self.dealer.hand.value == hand.value:
                    if self.dealer.hand.blackjack():
                        status = "LOST"  # player's non-bj 21 vs dealers blackjack
                    else:
                        status = "PUSH"
        else:
            status = "SURRENDER"


        if status == "LOST":
            win += -1
        elif status == "WON":
            win += 1
        elif status == "WON BLACKJACK":
            win += BLACKJACK_PAYOUT #variable set at start
        elif status == "SURRENDER":
            win += -0.5
            
        if hand.doubled:
            win *= 2
            bet *= 2

        win *= self.stake
        
        self.win = win
        self.status = status
        
        print(status_info)
        
        return win, bet, status

    def play_round(self):
        if self.player.autoplay:
            #if counting very favorable - bet high
            if self.shoe.truecount() >= TRUE_COUNT_TOP: 
                self.stake = SIZE_OF_BET * TOP_BET_SPREAD
            #if counting moderately favorable - bet mid
            elif self.shoe.truecount() >= TRUE_COUNT_MID: 
                self.stake = SIZE_OF_BET * MID_BET_SPREAD
            #if counting is not favorable - bet low (regular)
            else:
                self.stake = SIZE_OF_BET
        else:
            raw_stake = input("BET (%s): " % self.stake)
            if raw_stake != "":
                try:
                    self.stake = float(raw_stake)
                except ValueError:
                    print("Invalid bet, using default.")
        
        #OLD DEALING
        #player_hand = Hand([self.shoe.deal(), self.shoe.deal()])
        #dealer_hand = Hand([self.shoe.deal()])
        #CORRECTED DEALING
        player_hand = Hand([self.shoe.deal()])
        dealer_hand = Hand([self.shoe.deal()])
        player_hand.add_card(self.shoe.deal())
        dealer_hand.add_card(self.shoe.deal())
        
        self.player.set_hands(player_hand, dealer_hand)
        self.dealer.set_hand(dealer_hand)
        
        
        print("DEALER HAND: %s (%d)" % (self.dealer.hand, self.dealer.hand.value))
        #print("DEALER HAND: %s" % (self.dealer.hand.cards[0]))
        print("PLAYER HAND: %s (%d)" % (self.player.hands[0], self.player.hands[0].value))

        self.player.play(self.shoe)
        
        #NOT SURE WHY NOT DO THIS INSTEAD OF CHECKING TO SEE IF PLAYER BUSTED FIRST!
        #WHAT HAPPENS IF THE THE PLAYER SPLIT AND HIS FIRST HAND BUSTED BUT NOT HIS SECOND HAND?
        #CHECKED AND THE PLAYER PROPERLY LOSES IF BOTH DEALER AND PLAYER BUST
        #TODO: CHECK TO SEE IF THIS HAS THE DEALER PLAYS IF A SPLITTED FIRST HAND IS BUSTED
        #WHY NOT SIMPLY USE: self.dealer.play(self.shoe)
        
        self.dealer.play(self.shoe)
        '''
        if not self.player.hands[0].busted():
            self.dealer.play(self.shoe)
        else:
            dealer_hand.add_card(self.shoe.deal())
        '''



        for hand in self.player.hands:
            win, bet, status = self.get_hand_winnings(hand)
            self.money += win
            self.bet += bet
            
    def get_money(self):
        return self.money

    def get_bet(self):
        return self.bet


if __name__ == "__main__":
    #importer = StrategyImporter(sys.argv[1])
    importer = StrategyImporter(sys.argv) #fixes "IndexError: list index out of range"
    HARD_STRATEGY, SOFT_STRATEGY, PAIR_STRATEGY = (
        importer.import_player_strategy())

    bankroll = [] #moneys each round
    moneys = [] #moneys each shoe
    bets = []
    countings = []
    nb_hands = 0
    game_num = 0
    #NUM_GAMES = int(input("How many games? "))
     
    #for g in range(NUM_GAMES):
    while nb_hands < NUM_HANDS:
        game_num += 1
        game = Game()
        #autoplay = input("Autoplay? (y/n): ")
        autoplay = 'y'
        if autoplay == 'n':
            game.player.autoplay = False
        while not game.shoe.reshuffle:
            print('%s GAME no. %d - Hand %d %s' % (20 * '#', game_num, nb_hands, 20 * '#'))
            
            game.play_round()
                        
            print("DEALER HAND: %s (%d)" % (game.dealer.hand, game.dealer.hand.value))
            #IF SPLIT, PRINT ALL THE DIFFERENT HANDS
            number_of_current_hands = len(game.player.hands)
            for x in range(number_of_current_hands):
                print("PLAYER HAND: %s (%d)" % (game.player.hands[x], game.player.hands[x].value))
            print("CURRENT BET: %s" % "{0:.2f}".format(game.stake))
            if game.player.hands[0].doubled:
                print("DOUBLE")
            print('%s %s' % (game.status, game.win))
            print("GAME BANKROLL: %s" % "{0:.2f}".format(game.get_money()))
            print("GAME BETS: %s" % "{0:.2f}".format(game.get_bet()))
            print("TRUE COUNT: %s" % "{0:.2f}".format(game.shoe.truecount()))
            print("REG COUNT: %s" % "{0:.2f}".format(game.shoe.regcount()))
            
            
            bankroll.append(game.get_money())
            
            nb_hands += 1


        moneys.append(game.get_money())
        bets.append(game.get_bet())
        countings += game.shoe.count_history

        #print("WIN for Game no. %d: %s (%s bet) - %s" % (g + 1, "{0:.2f}".format(game.get_money()), "{0:.2f}".format(game.get_bet()), nb_hands))
        print("WIN for Game no. %d: %s (%s bet) - %s" % (game_num, "{0:.2f}".format(game.get_money()), "{0:.2f}".format(game.get_bet()), nb_hands))

    if game.player.autoplay is False:
        game.player.history.save()
    sume = 0.0
    total_bet = 0.0
    for value in moneys:
        sume += value
    for value in bets:
        total_bet += value

    print("\n%d hands overall, %0.2f hands per game on average" %
          (nb_hands, float(nb_hands) / game_num))
    print("%0.2f total bet" % total_bet)
    print("Overall winnings: {} (edge = {} %)".format(
            "{0:.2f}".format(sume), "{0:.3f}".format(100.0 * sume / total_bet))
          )
    
    '''
    moneys = sorted(moneys)
    fit = stats.norm.pdf(moneys, np.mean(moneys), np.std(moneys))
    pl.plot(moneys, fit, '-o')
    pl.hist(moneys, normed=True)
    pl.show()
    '''
    
    plt.ylabel('count')
    plt.plot(countings, label='x')
    plt.legend()
    plt.show()
    
    plt.ylabel('money')
    plt.plot(bankroll, label='x')
    #plt.plot(moneys, label='x')
    plt.legend()
    plt.show()

    #print(StrategyImporter.soft_strategy)
    
    
'''
NOTES: 
    
CASINO RULES: 
 - Dealer blackjack ends: NEED TO IMPLEMENT
 - The simulator plays with the following casino rules:
 - Dealer stands on soft 17
 - Double down after splitting hands is allowed
 - No BlackJack after splitting hands
 - 3 times 7 is counted as a BlackJack
 - blackjack pays 3:2

#TODO: Need to implement variables for these rules
 - Dealer hits/stands on soft 17 - DONE!
 - Player can double after split 
 - Player can double on any, 9-11, 10-11
 - Player can resplit to 2, 3, or 4 hands
 - Player can resplit aces
 - Player can hit split aces
 - Surrender rule: none, late
 - Blackjack pays: 3:2 (1.5) or 6:5 (1.2) - DONE!
 - Number of Decks - DONE!

LEGEND:
A Hand is a single hand of Blackjack, consisting of two or more cards
A Round is single round of Blackjack, in which one or more players play their hands against the dealer's hand
A Shoe consists of multiple card decks consisting of SHOE_SIZE times 52 cards
A Game is a sequence of Rounds that starts with a fresh Shoe and ends when the Shoe gets reshuffled

CALCUlATE HOUSE EDGE
To differentiate a winrate of WR from (1-f)*WR, you need (z*SD/WR/f)^2 hands. So for a typical blackjack game with WR = -0.01, SD = 1.15, z = 2 (1-sided certainty of 98%), and f = .1 (WR is more than 10% off), you're looking at about 5 million hands.

POSSIBLE BETTING STRATEGY
COUNT - BET 
-2      1x  $0
-1      1x  $25
0       1x  $50
1       1x  $100
2       2x  $100
3       2x  $150
4       2x  $200

'''
