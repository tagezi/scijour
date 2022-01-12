#     This code is a part of program Science Articles Orderliness
#     Copyright (C) 2021  Valerii Goncharuk (aka tagezi)
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

import time

from lib.sqlmain import *
from lib.strmain import *
from lib.perfect_soup import *
import config


def set_update(sValue, iID, sTable, sColumnValue, sColumnID):
    cValues = (sValue, iID,)
    oConnect.update(sTable, sColumnValue, sColumnID, cValues)


def get_parameters(sURL, sName, sShortName, sDBTable, iDBID, sDBName):
    time.sleep(2)

    bsWikiPage = PerfectSoup(sURL)
    if bsWikiPage is None:
        return None
    if sName is None:
        sName = clean_parens(bsWikiPage.get_title_h1())
        if sName == 'Monumenta Nipponica':
            return None

    iID = oConnect.sql_get_id(sDBTable, iDBID, sDBName, (sName,))
    if not iID:
        oConnect.insert_row(sDBTable, sDBName, (sName,))
        iID = oConnect.sql_get_id(sDBTable, iDBID, sDBName, (sName,))
        set_update(sURL, iID, sDBTable, 'wiki_url', iDBID)
        if sShortName is not None:
            set_update(sShortName, iID, sDBTable, 'short_name', iDBID)

    lHtmlListName = bsWikiPage.findAll("th", {"infobox-label"})
    lHtmlListValues = bsWikiPage.findAll("td", {"infobox-data"})
    sHTML = bsWikiPage.find("table", {"infobox hproduct"})
    if sHTML is not None:
        sHTML = sHTML.find("td", {"infobox-full-data"})
        if sHTML:
            sHTML = sHTML.findAll("li")

    lListName = []
    for name in lHtmlListName:
        lListName.append(name.get_text())

    dValues = dict()
    dValues['Name'] = sName
    dValues['ID'] = iID
    dValues['ListName'] = lListName
    dValues['ListValues'] = lHtmlListValues
    dValues['HTML'] = sHTML

    return dValues


def get_pub_name(sPub):
    sPubName = clean_parens(sPub.get_text())
    sPubURL = None
    sShortPubName = None
    sAPub = sPub.find("a")
    if sAPub is not None and sPubName.find(sAPub.get_text()) \
            and oConnect.q_get_id_country(sAPub.get_text()):

            sPubName = clean_parens(sAPub.get_text())
            if str(sAPub).find("href") != -1 and \
                    str(sAPub).find("redlink") == -1:
                sPubURL = "https://en.wikipedia.org" + str(sAPub.attrs['href'])

                bsPubPage = PerfectSoup(sPubURL)
                if bsPubPage is not None:
                    partHTML = bsPubPage.find("div", {
                        "class": "mw-parser-output"}).findAll("p",
                                                              {'class': None})
                    lBolsTag = []
                    for sPTag in partHTML:
                        lBolsTag = sPTag.findAll("b")
                        if lBolsTag:
                            break

                    k = int(0)
                    for sBold in lBolsTag:
                        try:
                            if int(k) == int(0):
                                sPubName = sBold.string

                            elif int(k) == int(1):
                                if len(sPubName) < len(sBold.string):
                                    sShortPubName = sPubName
                                    sPubName = sBold.string
                                else:
                                    sShortPubName = sBold.string
                        except ValueError as e:
                            print(e)
                        k = k + 1

    if not oConnect.q_get_id_publisher(sPubName):
        if sPubURL is not None:
            get_pub_parameters(sPubURL, sPubName, sShortPubName)
        else:
            oConnect.insert_row('Publisher', 'publisher_name',
                                (sPubName,))

    return sPubName


def get_pub_parameters(sURLPubl, sPublName, sShortPublName):
    dValues = get_parameters(sURLPubl, sPublName, sShortPublName, 'Publisher',
                             'id_publisher', 'publisher_name')

    if dValues is None:
        return

    i = 0
    for sProperty in dValues['ListValues']:

        iID = dValues['ID']
        if dValues['ListName'][i] == ("Parent company" or "Owner(s)"):
            sPubName = get_pub_name(sProperty)
            iPubID = oConnect.q_get_id_publisher(sPubName)
            oConnect.q_update_publisher('mother_company',
                                        (iPubID, iID))

        elif dValues['ListName'][i] == "Founded":
            lFounded = get_values(sProperty.get_text())
            sCFounded = lFounded[(len(lFounded) - 1)]
            sFounded = lFounded[0]
            if len(sFounded) > 4:
                lFounded = sFounded.split(" ")
                sFounded = clean_parens(lFounded[(len(lFounded) - 1)])

            oConnect.q_update_publisher('creation_year', (sFounded, iID,))
            iIdCo = oConnect.q_get_id_country(sCFounded)
            if iIdCo:
                oConnect.q_update_publisher('creation_country', (iIdCo, iID,))

        elif dValues['ListName'][i] == "Headquarters location":
            lCountry = dValues["ListName"][i].split(", ")
            iIdCo = oConnect.q_get_id_country(lCountry[len(lCountry) - 1])
            if iIdCo:
                oConnect.q_update_publisher('id_country', (iIdCo, iID,))

        elif dValues['ListName'][i] == "Country of origin":
            iIdCo = oConnect.q_get_id_country(sProperty.get_text())
            if iIdCo:
                oConnect.q_update_publisher('creation_country', (iIdCo, iID,))

        elif dValues['ListName'][i] == ("Official website" or "Website"):
            sLink = str(sProperty.find("a").attrs['href'])
            oConnect.q_update_publisher('website', (sLink, iID))

        elif dValues['ListName'][i] == "Status":
            sStatus = sProperty.get_text()
            oConnect.q_update_publisher('status', (sStatus, iID))

        elif dValues['ListName'][i] == "Founder":
            sFounder = sProperty.get_text()
            oConnect.q_update_publisher('founder', (sFounder, iID))

        i = i + 1


def get_book_parameters(sURL):
    dValues = get_parameters(sURL, None, None, 'Book', 'id_book', 'book_name')
    if dValues is None or dValues['HTML'] is None:
        return

    iID = dValues['ID']
    for link in dValues['HTML']:
        if link.get_text() == ("Journal homepage" or
                               "Online access" or "Online archive"):
            sLink = str(link.find("a").attrs['href'])
            oConnect.q_update_book('book_homepage', (sLink, iID,))

    i = 0
    for sProperty in dValues['ListValues']:

        # dspln is accepted abbreviation of word 'discipline'
        if dValues['ListName'][i] == "Discipline":
            sDspln = sProperty.get_text()
            lDspln = get_values(sDspln)
            for sDspln in lDspln:
                iDspln = oConnect.q_get_id_dspln(sDspln)
                if iDspln:
                    oConnect.q_insert_dspln(sDspln)
                oConnect.q_insert_book_dspln((iID, iDspln,))

        elif dValues['ListName'][i] == "Language":
            sLang = sProperty.get_text()
            lLang = get_values(sLang)
            for sLang in lLang:
                iLang = oConnect.q_get_id_lang_by_name(sLang)
                oConnect.q_insert_book_lang((iID, iLang,))

        elif dValues['ListName'][i] == "Edited by":
            lEdited = get_values(sProperty.get_text())
            for sEdited in lEdited:
                oConnect.q_insert_book_editor((iID, sEdited,))

        elif dValues['ListName'][i] == "History":
            nums = re.findall(r'\d+', sProperty.get_text())
            iYear = [int(i) for i in nums]
            oConnect.q_update_book('creation_year', (iYear[0], iID,))

        elif dValues['ListName'][i] == "Publisher":
            sPubName = get_pub_name(sProperty)
            iPubID = oConnect.q_get_id_publisher(sPubName)
            oConnect.q_update_book('publisher', (iPubID, iID,))

        elif dValues['ListName'][i] == "Frequency":
            sFrequency = sProperty.get_text()
            oConnect.q_update_book('book_frequency', (sFrequency, iID,))
        elif dValues['ListName'][i] == "ISO 4":
            sISO4 = sProperty.get_text()
            oConnect.q_update_book('iso_4', (sISO4, iID,))

        elif dValues['ListName'][i] == "ISSN":
            lISSN = sProperty.findAll("a")
            sISSN = lISSN[0].get_text()
            oConnect.q_update_book('issn_print', (sISSN, iID,))

            if len(lISSN) == 2:
                sISSN = lISSN[1].get_text()
                oConnect.q_update_book('issn_web', (sISSN, iID,))

        elif dValues['ListName'][i] == "LCCN":
            sLCCN = sProperty.get_text()
            oConnect.q_update_book('lccn', (sLCCN, iID,))

        elif dValues['ListName'][i] == "OCLC no.":
            sOCLC = sProperty.get_text()
            oConnect.q_update_book('oclc_no', (sOCLC, iID,))

        i = i + 1


if __name__ == '__main__':
    wiki_sources = get_filename_patch(config.files_dir, config.wiki_source)
    oConnect = Sqlmain(config.db_file)

    with open(wiki_sources, "r") as f:
        for sURL in f:
            bsObj = PerfectSoup(sURL)
            if bsObj is None:
                continue
            lListURl = bsObj.get_link_from_list()
            for URL in lListURl:
                get_book_parameters("https://en.wikipedia.org" + URL)
