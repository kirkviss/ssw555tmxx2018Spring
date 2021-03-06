#Authors: Max Remetz, Adam Bannat, Kirk Visser, Shashank Mysore Bhagwan
#We pledge our honor that we have abided by the Stevens Honor System
#Date: 2/6/2018

import os
import collections
import datetime
import sys
import dateutil.relativedelta
from prettytable import PrettyTable

#Dictionaries to store unsorted individuals and families
indis = {}
fams = {}

#Gloabl individual and family collections
individuals = {}
families = {}

# All hard code string values to change to global values  
Birthday = "Birthday"
Death = "Death"
Marriage = "Marriage"
Divorce = "Divorce"
Name = "Name"
Gender = "Gender"
Child = "Child"
Spouse = "Spouse"
HusbandId = "Husband ID"
HusbandName = "Husband Name"
WifeId = "Wife ID"
WifeName = "Wife Name" 

#dictionaries holding tags and respective values for easier handling of dicts
dateTags = {"BIRT": Birthday, "DEAT": Death, "MARR": Marriage, "DIV": Divorce}
indiTags = {"NAME": Name , "SEX": Gender, "FAMC": Child, "FAMS": Spouse}
famTags = {"HUSB": [HusbandId, HusbandName], "WIFE": [WifeId, WifeName]}
monthNums = {"JAN": "01", "MAR": "03", "MAY": "05", "JUL": "07", "AUG": "08", "OCT": "10", "DEC": "12", "APR": "04", "JUN": "06", "SEP" : "09","NOV": "11", "FEB": "02"}

printErrors = []

#Main function which parses through GEDCOM file, stores individuals and
#families in dictionaries, sorts dictionaries into collections
#then finally pretty prints collections
def gedcomParser():
    if (len(sys.argv) > 1 and sys.argv[1][-4:] == ".ged"):
        infile = open(sys.argv[1], "r")
    else:
        infile = open("testfile.ged", "r")
    currId = "0"
    currDict = {}
    Date = ""
    for line in infile:
        if line[0] == "0":
            parts = zeroLine(line.split())
            if parts[1] == "INDI":
                currId = parts[2]
                #US22
                if currId in indis.keys():
                    printErrors.append("ERROR: INDIVIDUAL: US22: id " + currId + " already found. Previous individual has been replaced.")
                indis[currId] = {Death: "N/A", "Alive": "True", Spouse:
                                 "N/A", Child: "N/A"}
                currDict = indis
            if parts[1] == "FAM":
                currId = parts[2]
                fams[currId] = {"Children": [], Divorce: "N/A"}
                currDict = fams
        elif line[0] == "1":
            parts = oneLine(line.split())
            if parts[1] in dateTags.keys():
                Date = dateTags[parts[1]]
                if Date == Death:
                    indis[currId]["Alive"] = "False"
            elif parts[1] in indiTags.keys():
                tag = indiTags[parts[1]]
                value = ""
                for s in parts[2:-1]:
                    value += s + " "
                indis[currId][tag] = value[:-1]
            else:
                if parts[1] in famTags:
                    tags = famTags[parts[1]]
                    fams[currId][tags[0]] = parts[2]
                    fams[currId][tags[1]] = indis[parts[2]][Name ]
                else:
                    fams[currId]["Children"].append(parts[2])
        elif line[0] == "2":
            parts = twoLine(line.split())
            dateStr = parts[4] + '-' + monthNums[parts[3]] + '-' + parts[2]
            currDict[currId][Date] = dateStr
            printErrors.append(dateHasPassed(dateStr, currDict, currId, Date))
        else:
            parts = line.split()
            parts.append("N")
    for i in indis:
        indis[i]["Age"] = getAge(i)

    individuals = collections.OrderedDict(sorted(indis.items()))
    prettyIndi = PrettyTable(["Id", Name , Birthday, Gender, "Age",
                             "Alive", Death, Child, Spouse])
    for k,v in individuals.items():
        row = list([k, v[Name], v[Birthday], v[Gender], v["Age"], v["Alive"],
              v[Death], v[Child], v[Spouse]])
        prettyIndi.add_row(row)
    print("Individuals")
    print(prettyIndi)
    families = collections.OrderedDict(sorted(fams.items()))
    prettyFam = PrettyTable(["Id", "Married", "Divorced", HusbandId,
                             HusbandName, WifeId, WifeName,
                             "Children"])
    for k,v in families.items():
        v['Children'] = orderSiblings(k, v['Children'])
        row = list([k, v[Marriage], v[Divorce], v[HusbandId],
                             v[HusbandName], v[WifeId], v[WifeName],
                             v["Children"]])
        prettyFam.add_row(row)
    print("Families")
    print(prettyFam)

    #US23
    sameNameAndBirth(individuals)

    #Invalid date errors
    for err in printErrors:
        if len(err) > 0:
            print(err)

    #Individual Checks
    for k,v in individuals.items():
        birthBeforeDeath(k, v[Birthday], v[Death])
        ageLessThanOneFifty(k, v["Age"])
        birthdayOfLivingPeople(k, v['Name'], v['Birthday'])
    
    #Marriage and Living Checks
    orphans = []
    for k,v in individuals.items():
        listDeceased(k, v)
        listLivingMarried(k, v)
        listLivingSingle(k, v)
        listRecentBirths(k, v["Birthday"])
        listRecentDeaths(k, v["Death"])
        if v['Child'] != "N/A":
            if isOrphan(k):
                name = v[Name]
                orphans.append(name)
    print("INDIVIDUALS: US33: The following children are orphans: ", str(orphans))


    #Family checks
    for k,v in families.items():
        marriageBeforeDivorce(k, v)
        marriageBeforeDeath(k, v[Marriage],v[HusbandId], individuals[v[HusbandId]][Death], v[WifeId], individuals[v[WifeId]][Death])
        divorceBeforeDeath(k, v[Divorce], v[HusbandId], individuals[v[HusbandId]][Death], v[WifeId], individuals[v[WifeId]][Death])
        birthBeforeMarriage(k, v[Marriage], v[HusbandId], individuals[v[HusbandId]][Birthday], v[WifeId], individuals[v[WifeId]][Birthday])
        fewerThanFifteen(k,v["Children"],v["Husband Name"],v["Wife Name"])
        husbIsFemale(k,v['Husband ID'],v['Husband Name'],individuals[v['Husband ID']]['Gender'])
        wifeIsMale(k,v['Wife ID'],v['Wife Name'],individuals[v['Wife ID']]['Gender'])
        checkMarriageAges(k, v)

        for child in v['Children']: 
            birthBeforeMarriageOfParents(v[HusbandId], v[WifeId], v[Marriage],child, individuals[child][Birthday])
            birthBeforeDeathOfParent(v[HusbandId], individuals[v[HusbandId]][Death], v[WifeId], individuals[v[WifeId]][Death], child,individuals[child][Birthday])
            parentsAgeCheck(v[HusbandId], individuals[v[HusbandId]][Birthday], v[WifeId], individuals[v[WifeId]][Birthday], child, individuals[child][Birthday])
     
     
        husbWifeNotSiblings(k, v[HusbandId], indis[v[HusbandId]][Child], v[WifeId], indis[v[WifeId]][Child])
        husbWifeNotCousins(k, v[HusbandId], indis[v[HusbandId]][Child], v[WifeId], indis[v[WifeId]][Child])
        anniversaryOfHusbAndWife(k,v['Marriage'], v['Husband Name'], v['Wife Name'])



#US27
def getAge(Id):
    currDate = datetime.date.today()
    birth = list(map(int, indis[Id][Birthday].split("-")))
    birthDate = datetime.date(birth[0], birth[1], birth[2])
    days = 0
    if indis[Id]["Alive"] == "False":
        death = list(map(int, indis[Id][Death].split("-")))
        currDate = datetime.date(death[0], death[1], death[2])
    days = (currDate-birthDate).days
    years = days/365
    return(str(int(years)))

#Function to evaluate and reformat 0 level lines
def zeroLine(ln):
    if len(ln) > 2:
        if ln[2] == "INDI" or ln[2] == "FAM":
            return [ln[0], ln[2], ln[1], "Y"]
        elif ln[1] == "NOTE":
            ln.append("Y")
            return ln
        else:
            ln.append("N")
            return ln
    elif ln[1] == "HEAD" or ln[1] == "TRLR":
        if len(ln) == 2:
            ln.append("Y")
            return ln
        else:
            ln.append("N")
            return ln
    else:
        ln.append("N")
        return ln

#Function to evaluate and reformat 1 level lines
def oneLine(ln):
    if ln[1] == Name :
        if len(ln) == 2 or (len(ln) > 2 and ln[-1][0] + ln[-1][-1] != "//"):
            ln.append("N")
            return ln
        ln.append("Y")
        return ln
    if ln[1] == "SEX":
        if len(ln) == 3 and (ln[2] == "M" or ln[2] == "F"):
            ln.append("Y")
            return ln
        ln.append("N")
        return ln
    if ln[1] == "BIRT" or ln[1] == "DEAT" or ln[1] == "MARR" or ln[1] == "DIV":
        if len(ln) == 2:
            ln.append("Y")
            return ln
        ln.append("N")
        return ln
    if ln[1] == "FAMC" or ln[1] == "FAMS" or ln[1] == "HUSB" or ln[1] == "WIFE" or ln[1] == "CHIL" :
        if len(ln) == 3:
            ln.append("Y")
            return ln
        ln.append("N")
        return ln
    ln.append("N")
    return ln

#Function to evaluate and reformat 2 level lines
def twoLine(ln):
    months = ["JAN", "MAR", "MAY", "JUL", "AUG", "OCT", "DEC", "APR", "JUN",
              "SEP","NOV", "FEB"]
    if ln[1] == "DATE" and len(ln) == 5:
        if ln[3] not in months or int(ln[2]) > 31 or int(ln[2]) < 1:
            ln.append("N")
            return ln
        elif int(ln[2]) == 31 and ln[3] not in months[0:]:
            ln.append("N")
            return ln
        elif int(ln[2]) > 29 and ln[3] == "FEB":
            ln.append("N")
            return ln
        else:
            ln.append("Y")
            return ln
    ln.append("N")
    return ln

#US01: Function to check if a date is before the current date
def dateHasPassed(date, currDict, currId, dateType):
    currDate = datetime.date.today()
    checkDate = list(map(int, date.split('-')))
    if (datetime.date(checkDate[0], checkDate[1], checkDate[2]) -
        currDate).days > 0:
        if(currDict == fams):
            return("Error: FAMILY: US01:" + currId + ": " + dateType + " on " + date + " has not happened yet as of " + str(datetime.date.today()))
        if(currDict == indis):
            return("ERROR: INDIVIDUAL: US01: " + currId +": "+ dateType + " on " + date + " has not happened yet as of " + str(datetime.date.today()))
    return ""

#US02: Function to check that birth is before marriage
def birthBeforeMarriage(k, marriage, husbandId, husbandBirth, wifeId, wifeBirth):
    #Do not compare if null
    if marriage == "N/A":
        return 0

    error = 0
    #check husband birth
    if husbandBirth != "N/A" and husbandBirth > marriage:
        print("ERROR: FAMILY: US02: " + str(k) + ": Married " + str(marriage) + \
        " before husband's (" + husbandId + ") birth on " + str(husbandBirth))
        error = 1
    #check wife birth
    if wifeBirth != "N/A" and wifeBirth > marriage:
        print("ERROR: FAMILY: US02: " + str(k) + ": Married " + str(marriage) + \
        " before wife's (" + wifeId + ") birth on " + str(wifeBirth))
        error = 1

    return error


#US03: Function to check that birth comes before death
def birthBeforeDeath(k, birthday, death):
    #Do not compare if null
    if death == "N/A" or birthday == "N/A":
        return 0

    if death < birthday:
        print ("ERROR: INDIVIDUAL: US03: " + str(k) + " Died " + str(death) + " before Born " + str(birthday))
        return 1
    else:
        return 0

#US04 -- marriage before divorce
#same as US03, may want to simpley combined these stories to create one
def marriageBeforeDivorce(familyItem, value):
    
    marriage = value[Marriage]
    divorce = value[Divorce]
    status_na = "N/A"

    if marriage == "N/A" or divorce == "N/A":
            return 0
    
    elif marriage > divorce:
        print ("ERROR: FAMILY: USO4: " + str(familyItem) + " Divorced " + str(divorce) + " before Married " + str(marriage))
        return 1

    else:
        return 0

#US05
def marriageBeforeDeath(familyItem, marriage, husbandId, husbandDeath, wifeId, wifeDeath):
    if marriage == "N/A":
        return 0
    
    binary_bol = 0
    if husbandDeath != "N/A" and husbandDeath < marriage:
        print("ERROR: FAMILY: US05: " + str(familyItem) + ": marriage " + str(marriage) +  "after husband's (" + husbandId + ") death on " + str(husbandDeath))
        binary_bol = 1
    if  wifeDeath != "N/A" and wifeDeath < marriage: 
        print("Error: FAMILY: US05 " + str(familyItem) + ": marriage " + str(marriage) + "after wife's (" + wifeId + ") death on " + str(wfieDeath))
        binary_bol = 1 

    return binary_bol



#US06
def divorceBeforeDeath(k, divorce, husbandId, husbandDeath, wifeId, wifeDeath):
    #Do not compare if null
    if divorce == "N/A":
        return 0

    error = 0
    #check husband death
    if husbandDeath != "N/A" and husbandDeath < divorce:
        print("ERROR: FAMILY: US06: " + str(k) + ": Divorced " + str(divorce) + \
        " after husband's (" + husbandId + ") death on " + str(husbandDeath))
        error = 1
    #check wife death
    if wifeDeath != "N/A" and wifeDeath < divorce:
        print("ERROR: FAMILY: US06: " + str(k) + ": Divorced " + str(divorce) + \
        " after wife's (" + wifeId + ") death on " + str(wifeDeath))
        error = 1

    return error


#US07
def ageLessThanOneFifty(k, age):
    if age == "N/A":
        return 0

    if int(age) > 150 or int(age) < 0:
        print("ERROR: INDIVIDUAL: US07: " + str(k) + " age " + str(age) + " is older than 150 or less than 0.")
        return 1
    else:
        return 0


#US08
def birthBeforeMarriageOfParents( husbandId, wifeId, marriage, childId, childBirthday):
    
    err = 0
    
    if marriage == "N/A" or childId == "N/A":
        return err

    if marriage > childBirthday:
        print("ERROR: FAMILY: US08: Child: " + childId + "'s birthday is before the marriage of husband " + husbandId +" and wife " + wifeId)
        err = 1

    return err 

#US09 Parents not too old 
# Mother's death should after the birth of the child
# Father's death should be after at least 9 months before the birth of the child
def birthBeforeDeathOfParent(husbandId, husbandDeath, wifeId, wifeDeath, childId, childBirthday):
     
    err = 0

    if childId == "N/A" or (husbandDeath == "N/A" and wifeDeath == "N/A"):
        return err

    if not (wifeDeath == "N/A") and wifeDeath < childBirthday:
        err = 1 
        print("ERROR: FAMILY: US09: Child: " + childId + "'s birthday is after the death of their mother " + wifeId)


    if not (husbandDeath == "N/A") and (datetime.datetime.strptime(husbandDeath, '%Y-%m-%d') + dateutil.relativedelta.relativedelta(months=9)) < datetime.datetime.strptime( childBirthday, '%Y-%m-%d')  :
        err = 1
        print("ERROR: FAMILY: US09: Child: " + childId + "'s birthday is over 9 months after the death of their father " + husbandId)
         
    return err

#US12 Parents
# Mother should be less than 60 years older than her children and father should be less than 80 years older than his children
def parentsAgeCheck(husbandId, husbandBirth, wifeId, wifeBirth, childId, childBirth):
    err = 0 

    if childId == 'N/A' or husbandId == 'N/A' or wifeId == 'N/A':
        return 0

    date_type_husbandBirth = datetime.datetime.strptime(husbandBirth, '%Y-%m-%d')
    date_type_wifeBirth = datetime.datetime.strptime(wifeBirth, '%Y-%m-%d')
    date_type_childBirth = datetime.datetime.strptime(childBirth,'%Y-%m-%d' )

    # print (dateutil.relativedelta.relativedelta(date_type_husbandBirth, date_type_childBirth).years)
    if dateutil.relativedelta.relativedelta(date_type_childBirth, date_type_husbandBirth).years >= 80:
        err = 1
        print("ERROR: FAMILY: US12: " + husbandId + " is too old to be the father of " + childId)

    if dateutil.relativedelta.relativedelta( date_type_childBirth, date_type_wifeBirth).years >= 60:
        err = 1
        print("ERROR: FAMILY: US12: " + wifeId + " is too old to be the mother of " + childId)

    return err



#US15
def fewerThanFifteen(familyItem, anArray, husbName, wifeName):

    if husbName == "N/A" or wifeName == "N/A":
        return 0


    if(len(anArray) > 14):
        print("ERROR: FAMILY: US15: "+ str(husbName) + " and " +str(wifeName)+ " have more than 15 children")
        return 1
    else:
        return 0


#US18
def husbWifeNotSiblings(k, husbID, husbFam, wifeID, wifeFam):
        if husbFam != 'N/A' and (husbFam == wifeFam):
                print('ERROR: FAMILY: US18: ' + k + ": husband (" + husbID + ") and wife (" + wifeID + ") are siblings.")
                return 1
        else:
                return 0

#US19
def get_fams(famc):
    dad = fams[famc]['Husband ID']
    mom = fams[famc]['Wife ID']
    return [indis[dad]['Child'], indis[mom]['Child']]

def husbWifeNotCousins(k, husbID, husbFam, wifeID, wifeFam):
    error = 0
    if husbFam != 'N/A' and wifeFam != 'N/A':
        hFams = get_fams(husbFam)
        wFams = get_fams(wifeFam)
        for fam in hFams:
            if fam in wFams and fam != 'N/A':
                error = 1
    if error == 1:
        print('ERROR: FAMILY: US19: '+ k + " Husband (" + husbID +") and wife ("
              + wifeID + ") are first cousins and married")
    return error

#US23
def sameNameAndBirth(individuals):
    namesAndBirths = []

    for k,v in individuals.items():
        namesAndBirths.append((v[Name], v[Birthday]))

    from collections import Counter

    c=collections.Counter(namesAndBirths)

    for k, v in c.most_common():
        if v > 1:
            print("ERROR: INDIVIDUAL: US23: Multiple (" +  str(v) + ") Individuals named " + str(k[0]) + " with same birthday found.")
            return 1
        else:
            return 0

#US29
def listDeceased(k, v):
    if v["Alive"] == 'False':
        print("INDIVIDUAL: US29: " + str(k) + " is deceased")
        return 0
    else:
        return 1

#US30
def listLivingMarried(k, v):
    if v["Alive"] == 'True' and 'N/A' not in v["Spouse"]:
        print("INDIVIDUAL: US30: " + str(k) + " is alive and married")
        return 0
    else:
        return 1

#US31
def listLivingSingle(k, v):
    if int(v["Age"]) > 30 and 'N/A' in v["Spouse"]:
        print("INDIVIDUAL: US31: " + str(k) + " is over 30 and single")
        return 0
    else:
        return 1

#US35
def listRecentBirths(k, birth):
    currDate = datetime.date.today()
    birthArray = list(map(int, birth.split('-')))
    birthDate = datetime.date(birthArray[0], birthArray[1], birthArray[2])
    daysSinceBirth = (currDate - birthDate).days

    if daysSinceBirth <= 30 and daysSinceBirth >= 0:
        print("INDIVIDUAL: US35: " + str(k) + " was born with the past 30 days")
        return 1
    return 0

#US36
def listRecentDeaths(k, death):
    if death == "N/A":
        return 0

    currDate = datetime.date.today()
    deathArray = list(map(int, death.split('-')))
    deathDate = datetime.date(deathArray[0], deathArray[1], deathArray[2])
    daysSinceDeath = (currDate - deathDate).days

    if daysSinceDeath <= 30 and daysSinceDeath >= 0:
        print("INDIVIDUAL: US36: " + str(k) + " has died with the past 30 days")
        return 1
    return 0


#US39	
def anniversaryOfHusbAndWife(familyItem, married, husbname, wifename):
    if husbname =="N/A" or wifename =="N/A":
        return 0

    currDate = datetime.date.today()
    checkDate = list(map(int, married.split('-')))
    if ((((currDate - datetime.date(checkDate[0], checkDate[1], checkDate[2])).days - ((currDate - datetime.date(checkDate[0], checkDate[1], checkDate[2]))/1460).days) % 365) )>= 335:
        print("ERROR: FAMILY: US39: Anniversary between " + husbname + " and " + wifename )
        return 1
    return 0


#US21
def husbIsFemale(familyItem,genderHusb, husbname, gender1):

    if genderHusb != "None":
        if gender1 == "F":
            print("ERROR: FAMILY: US21: " + str(husbname) + " is female")
            return 1
        else:
            return 0

#US21
def wifeIsMale(familyItem,genderHusb, wifename, gender2):

     if genderHusb != "None":
        if gender2 == "M":
            print("ERROR: FAMILY: US21: " + str(wifename) + " is male")
            return 1
        else:
            return 0

#US28
def orderSiblings(famID, children):
    ages = {id: indis[id]['Age'] for id in children}
    ordered_dict = collections.OrderedDict(sorted(ages.items())).items()
    ordered_list = [k for k, v in ordered_dict]
    return ordered_list

#US33
def isOrphan(childID):
    if int(indis[childID]['Age']) < 18:
        childFam = indis[childID]['Child']
        parents = [fams[childFam]['Husband ID'], fams[childFam]['Wife ID']]
        father = indis[parents[0]]
        mother = indis[parents[1]]
        if father["Death"] != "N/A" and mother["Death"] != "N/A":
            return True
        return False

#US34
def ageAtMarriage(Id):
    spouseFam = indis[Id]['Spouse']
    married = list(map(int, fams[spouseFam][Marriage].split("-")))
    marDate = datetime.date(married[0], married[1], married[2])
    birth = list(map(int, indis[Id][Birthday].split("-")))
    birthDate = datetime.date(birth[0], birth[1], birth[2])
    mAge = marDate - birthDate
    return int(mAge.days/365)

def checkMarriageAges(famID, fam):
    husbID = fam['Husband ID']
    wifeID = fam['Wife ID']
    hAge = ageAtMarriage(husbID)
    wAge = ageAtMarriage(wifeID)
    if hAge > (wAge * 2):
        print('FAMILY: US34: ', famID, ': At', str(hAge) + ', Husband', husbID, 'was over twice the age of Wife', wifeID + ',', str(wAge) + ', on the day of their marriage')
        
#US38
def birthdayOfLivingPeople(k, name, birthday):
    if name =="N/A" or birthday =="N/A":
        return 0

    currDate = datetime.date.today()
    checkDate = list(map(int, birthday.split('-')))
    if ((((currDate - datetime.date(checkDate[0], checkDate[1], checkDate[2])).days - (
            (currDate - datetime.date(checkDate[0], checkDate[1], checkDate[2])) / 1460).days) % 365)) >= 335:
        print("ERROR: INDIVIDUAL: US38: The birthday of " +str(name))
        return 1
    return 0

        
gedcomParser()
