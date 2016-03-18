#!/usr/bin/env python
from __future__ import print_function
import argparse
import re
import glob
import gdal
import osr
import subprocess
import lxml.etree
from lxml.builder import E
import math
import os
from os.path import isfile, isdir, join
import glob
import sys
import time, datetime
from time import gmtime, strftime
import pipes
import shutil
import psycopg2
import psycopg2.errorcodes
import optparse

FAKE_COMMAND = 0
DEBUG = True

DOWNLOADER_NUMBER_OF_CONFIG_PARAMS_FROM_DB = int(7)
SENTINEL2_SATELLITE_ID = int(1)
LANDSAT8_SATELLITE_ID = int(2)

MONTHS_FOR_REQUESTING_AFTER_SEASON_FINSIHED = int(2)

DATABASE_DEMMACCS_GIPS_PATH = "demmaccs.gips-path"
DATABASE_DEMMACCS_OUTPUT_PATH = "demmaccs.output-path"
DATABASE_DEMMACCS_SRTM_PATH = "demmaccs.srtm-path"
DATABASE_DEMMACCS_SWBD_PATH = "demmaccs.swbd-path"
DATABASE_DEMMACCS_MACCS_IP_ADDRESS = "demmaccs.maccs-ip-address"
DATABASE_DEMMACCS_MACCS_LAUNCHER = "demmaccs.maccs-launcher"
DATABASE_DEMMACCS_WORKING_DIR = "demmaccs.working-dir"


DATABASE_DOWNLOADER_STATUS_DOWNLOADING_VALUE = int(1)
DATABASE_DOWNLOADER_STATUS_DOWNLOADED_VALUE = int(2)
DATABASE_DOWNLOADER_STATUS_FAILED_VALUE = int(3)
DATABASE_DOWNLOADER_STATUS_ABORTED_VALUE = int(4)
DATABASE_DOWNLOADER_STATUS_PROCESSED_VALUE = int(5)

g_exit_flag = False

def run_command(cmd_array, use_shell=False):
    start = time.time()
    print(" ".join(map(pipes.quote, cmd_array)))
    res = 0
    if not FAKE_COMMAND:
        res = subprocess.call(cmd_array, shell=use_shell)
    print("App finished in: {}".format(datetime.timedelta(seconds=(time.time() - start))))
    if res != 0:
        print("Application error")
    return res


def signal_handler(signal, frame):
    global exitFlag
    print("SIGINT caught")
    exitFlag = True
    sys.exit(0)


def log(location, info, log_filename = None):
    if log_filename == None:
        log_filename = "log.txt"
    try:
        logfile = os.path.join(location, log_filename)
        if DEBUG:
            #print("logfile: {}".format(logfile))
            print("{}".format(info))
        log = open(logfile, 'a')
        log.write("{}:{}\n".format(str(datetime.datetime.now()),str(info)))
        log.close()
    except:
        print("Could NOT write inside the log file {}".format(logfile))
        
def create_recursive_dirs(dir_name):
    try:
        #create recursive dir
        os.makedirs(dir_name)
    except:
        pass
    #check if it already exists.... otherwise the makedirs function will raise an exception
    if os.path.exists(dir_name):
        if not os.path.isdir(dir_name):
            print("Can't create the directory because there is a file with the same name: {}".format(dir_name))
            print("Remove: {}".format(dir_name))
            return False
    else:
        #for sure, the problem is with access rights
        print("Can't create the directory due to access rights {}".format(dir_name))
        return False
    return True


def get_product_info(product_name):
    acquisition_date = None
    sat_id = 0
    print("product_name = {}".format(product_name))
    if product_name.startswith("S2"):
        m = re.match("\w+_V(\d{8}T\d{6})_\w+.SAFE", product_name)
        if m != None:
            sat_id = 1
            acquisition_date = m.group(1)
    elif product_name.startswith("LC8"):
        m = re.match("LC8\d{6}(\d{7})LGN\d{2}", product_name)
        if m != None:
            sat_id = 2
            acquisition_date = m.group(1)
            acquisition_date = strftime("%Y%m%dT%H%M%S", gmtime())
    print("get_product_info = {}".format(acquisition_date))
    return sat_id and (sat_id, acquisition_date)


def check_if_season(startSeason, endSeason, numberOfMonthsAfterEndSeason, yearArray):
#, logDir, logFileName):
    currentYear = datetime.date.today().year
    currentMonth = datetime.date.today().month
    #log(logDir, "{} | {}".format(startSeason, endSeason), logFileName)
    print("{} | {}".format(startSeason, endSeason))
    yearArray.append(currentYear)
    yearArray.append(currentYear)
    startSeasonMonth = int(startSeason[0:2])
    startSeasonDay = int(startSeason[2:4])
    endSeasonMonth = int(endSeason[0:2])
    endSeasonDay = int(endSeason[2:4])
    if startSeasonMonth < 1 or startSeasonMonth > 12 or startSeasonDay < 1 or startSeasonDay > 31 or endSeasonMonth < 1 or endSeasonMonth > 12 or endSeasonDay < 1 or endSeasonDay > 31:
        return False
    #log(logDir, "CurrentYear:{} | CurrentMonth:{} | StartSeasonMonth:{} | StartSeasonDay:{} | EndSeasonMonth:{} | EndSeasonDay:{}".format(currentYear, currentMonth, startSeasonMonth, startSeasonDay, endSeasonMonth, endSeasonDay), logFileName)
    print("CurrentYear:{} | CurrentMonth:{} | StartSeasonMonth:{} | StartSeasonDay:{} | EndSeasonMonth:{} | EndSeasonDay:{}".format(currentYear, currentMonth, startSeasonMonth, startSeasonDay, endSeasonMonth, endSeasonDay))
    #check if the season comprises 2 consecutive years (e.q. from october to march next year)
    if startSeasonMonth > endSeasonMonth:
        if currentMonth >= startSeasonMonth and currentMonth <= 12:
            yearArray[1] = currentYear + 1
        else:
            if currentMonth >= 1:
                yearArray[0] = currentYear - 1
    #log(logDir, "StartSeasonYear:{} | EndSeasonYear:{}".format(yearArray[0], yearArray[1]), logFileName)
    print("StartSeasonYear:{} | EndSeasonYear:{}".format(yearArray[0], yearArray[1]))
    currentDate = datetime.date.today()
    if currentDate < datetime.date(int(yearArray[0]), int(startSeasonMonth), int(startSeasonDay)) or currentDate > datetime.date(int(yearArray[1]), int(endSeasonMonth) + numberOfMonthsAfterEndSeason, int(endSeasonDay)):
        #log(logDir, "Current date is not inside or near the season", logFileName)
        return False
    return True


###########################################################################
class OptionParser (optparse.OptionParser):

    def check_required (self, opt):
      option = self.get_option(opt)
      # Assumes the option's 'default' is set to None!
      if getattr(self.values, option.dest) is None:
          self.error("{} option not supplied".format(option))

class Args(object):
    def __init__(self):
        self.general_log_path = "/tmp/"
        self.general_log_filename = "downloader.log"

###########################################################################
class Config(object):
    def __init__(self):
        self.host = ""
        self.database = ""
        self.user = ""
        self.password = ""
    def loadConfig(self, configFile):
        try:
            with open(configFile, 'r') as config:
                found_section = False
                for line in config:
                    line = line.strip(" \n\t\r")
                    if found_section and line.startswith('['):
                        break
                    elif found_section:
                        elements = line.split('=')
                        if len(elements) == 2:
                            if elements[0].lower() == "hostname":
                                self.host = elements[1]
                            elif elements[0].lower() == "databasename":
                                self.database = elements[1]
                            elif elements[0].lower() == "username":
                                self.user = elements[1]
                            elif elements[0].lower() == "password":
                                self.password = elements[1]
                            else:
                                print("Unkown key for [Database] section")
                        else:
                            print("Error in config file, found more than on keys, line: {}".format(line))
                    elif line == "[Database]":
                        found_section = True
        except:
            print("Error in opening the config file ".format(str(configFile)))
            return False
        if len(self.host) <= 0 or len(self.database) <= 0:
            return False
        return True


###########################################################################
class AOIContext(object):
    def __init__(self):
        # the following info will be fed up from database
        self.siteId = int(0)
        self.siteName = ""
        self.polygon = ""

        self.startSeasonMonth = int(0)
        self.startSeasonDay = int(0)
        self.endSeasonMonth = int(0)
        self.endSeasonDay = int(0)
        self.startSeasonYear = int(0)
        self.endSeasonYear = int(0)

        self.maxCloudCoverage = int(100)
        self.maxRetries = int(3)
        self.writeDir = ""
        self.aoiHistoryFiles = []
        self.aoiTiles = []
        #the following info will be fed up from the downloader arguments
        self.configObj = None
        self.remoteSiteCredentials = ""
        self.proxy = None
        #sentinel satellite only 
        self.sentinelLocation = ""
        #ed of sentinel satellite only
        #landsat only
        self.landsatDirNumber = None
        self.landsatStation = None
        #end of landsat only

    def addHistoryFiles(self, historyFiles):
        self.aoiHistoryFiles = historyFiles

    def appendHistoryFile(self, historyFile):
        self.aoiHistoryFiles.append(historyFile)

    def appendTile(self, tile):
        self.aoiTiles.append(tile)

    def setConfigParams(self, configParams):
        if len(configParams) != DOWNLOADER_NUMBER_OF_CONFIG_PARAMS_FROM_DB:
            return False
        startSummerSeason = configParams[0]
        endSummerSeason = configParams[1]
        startWinterSeason = configParams[2]
        endWinterSeason = configParams[3]
        self.maxCloudCoverage = int(configParams[4])
        self.maxRetries = int(configParams[5])
        self.writeDir = configParams[6]

        currentMonth = datetime.date.today().month
        # first position is the startSeasonYear, the second is the endPositionYear
        currentYearArray = []
        if check_if_season(startSummerSeason, endSummerSeason, MONTHS_FOR_REQUESTING_AFTER_SEASON_FINSIHED, currentYearArray):
            self.startSeasonMonth = int(startSummerSeason[0:2])
            self.startSeasonDay = int(startSummerSeason[2:4])
            self.endSeasonMonth = int(endSummerSeason[0:2])
            self.endSeasonDay = int(endSummerSeason[2:4])
        elif check_if_season(startWinterSeason, endWinterSeason, MONTHS_FOR_REQUESTING_AFTER_SEASON_FINSIHED, currentYearArray):
            self.startSeasonMonth = int(startWinterSeason[0:2])
            self.startSeasonDay = int(startWinterSeason[2:4])
            self.endSeasonMonth = int(endWinterSeason[0:2])
            self.endSeasonDay = int(endWinterSeason[2:4])
        else:
            print("Out of season ! No request will be made for {}".format(self.siteName))
            return False
        if len(currentYearArray) == 0:
            print("Something went wrong in check_if_season function")
            return False
        self.startSeasonYear = currentYearArray[0]
        self.endSeasonYear = currentYearArray[1]

        return True

    def fillHistory(self, dbInfo):
        self.aoiHistoryFiles = dbInfo

    def fileExists(self, filename):
        for historyFilename in self.aoiHistoryFiles:
            if filename == historyFilename:
                return True
        return False

    def setConfigObj(self, configObj):
        self.configObj = configObj

    def setRemoteSiteCredentials(self, filename):
        self.remoteSiteCredentials = filename

    def setProxy(self, filename):
        self.proxy = filename

    def setSentinelLocation(self, location):
        self.sentinelLocation = location
        
    def setLandsatDirNumber(self, dir_number):
        self.landsatDirNumber = dir_number

    def setLandsatStation(self, station):
        self.landsatStation = station

    def printInfo(self):
        print("SiteID  : {}".format(self.siteId))
        print("SiteName: {}".format(self.siteName))
        print("Polygon : {}".format(self.polygon))
        print("startS  : {}-{}-{}".format(self.startSeasonYear, self.startSeasonMonth, self.startSeasonDay))
        print("endS    : {}-{}-{}".format(self.endSeasonYear, self.endSeasonMonth, self.endSeasonDay))
        print("CloudCov: {}".format(self.maxCloudCoverage))
        print("general configuration: ")
        if self.configObj != None:
            print("configObj : {}|{}|{}|{}".format(self.configObj.host, self.configObj.database, self.configObj.user, self.configObj.password))
        else:
            print("configObj : None")
        print("remSiteCred: {}".format(self.remoteSiteCredentials))
        if self.proxy != None:
            print("proxy      : {}".format(self.proxy))
        else:
            print("proxy      : None")
        print("sentinelLocation: {}".format(self.sentinelLocation))
        if self.landsatDirNumber != None:
            print("landsatDirNumber: {}".format(self.landsatDirNumber))
        else:
            print("landsatDirNumber: None")
        if self.landsatStation != None:
            print("landsatStation: {}".format(self.landsatStation))
        else:
            print("landsatStation: None")

        if len(self.aoiTiles) <= 0:
            print("tiles: NONE")
        else:
            print("tiles:")
            print(" ".join(self.aoiTiles))

        if len(self.aoiHistoryFiles) <= 0:
            print("historyFiles: NONE")
        else:
            print("historyFiles:")
            print(" ".join(self.aoiHistoryFiles))


###########################################################################
class AOIInfo(object):
    def __init__(self, serverIP, databaseName, user, password, logFile):
        self.serverIP = serverIP
        self.databaseName = databaseName
        self.user = user
        self.password = password
        self.isConnected = False
        self.logFile = logFile

    def databaseConnect(self):
        if self.isConnected:
            return True
        try:
            connectString = "dbname='{}' user='{}' host='{}' password='{}'".format(self.databaseName, self.user, self.serverIP, self.password)
            print("connectString:={}".format(connectString))
            self.conn = psycopg2.connect(connectString)
            self.cursor = self.conn.cursor()
            self.isConnected = True
        except:
            print("Unable to connect to the database")
            self.isConnected = False
            return False
        return True

    def databaseDisconnect(self):
        if self.conn:
            self.conn.close()
            self.isConnected = False

    def getAOI(self, satelliteId):
        writeDirSatelliteName = ""
        if satelliteId == SENTINEL2_SATELLITE_ID:
            writeDirSatelliteName = "s2."
        elif satelliteId == LANDSAT8_SATELLITE_ID:
            writeDirSatelliteName = "l8."
        else:
            return False
        if not self.databaseConnect():
            return False
        try:
            self.cursor.execute("select *,st_astext(geog) from site")
            rows = self.cursor.fetchall()
        except:
            self.databaseDisconnect()
            return []
        # retArray will be a list of AOIContext
        retArray = []
        for row in rows:
            if len(row) == 5 and row[4] != None:
                # retry in case of disconnection
                if not self.databaseConnect():
                    return False
                currentAOI = AOIContext()
                currentAOI.siteId = int(row[0])
                currentAOI.siteName = row[2]
                currentAOI.polygon = row[4]
                #currentAOI.printInfo()
                baseQuery = "select * from sp_get_parameters(\'downloader."
                whereQuery = "where \"site_id\"="
                suffixArray = ["summer-season.start\')", "summer-season.end\')", "winter-season.start\')", "winter-season.end\')", "max-cloud-coverage\')", "{}max-retries')".format(writeDirSatelliteName), "{}write-dir\')".format(writeDirSatelliteName)]
                dbHandler = True
                configArray = []
                for suffix in suffixArray:
                    baseQuerySite = "{}{}".format(baseQuery, suffix)
                    query = "{} {} {}".format(baseQuerySite, whereQuery, currentAOI.siteId)
                    #print("query with where={}".format(query))
                    baseQuerySite += " where \"site_id\" is null"
                    try:
                        self.cursor.execute(query)
                        if self.cursor.rowcount <= 0:
                            self.cursor.execute(baseQuerySite)
                            if self.cursor.rowcount <= 0:
                                print("Could not get even the default value for downloader.{}".format(suffix))
                                dbHandler = False
                                break
                        if self.cursor.rowcount != 1:
                            print("More than 1 result from the db for downloader.{}".format(suffix))
                            dbHandler = False
                            break
                        result = self.cursor.fetchall()
                        #print("result={}".format(result))
                        configArray.append(result[0][2])
                    except Exception, e:
                        print("exception in query for downloader.{}:".format(suffix))
                        print("{}".format(e))
                        self.databaseDisconnect()
                        dbHandler = False
                        break
                print("-------------------------")
                if dbHandler:
                    if not configArray[-1].endswith("/"):
                        configArray[-1] += "/"
                    configArray[-1] += currentAOI.siteName
                    if not currentAOI.setConfigParams(configArray):
                        print("OUT OF THE SEASON !!!!")
                        continue
                    try:
                        #self.cursor.execute("select \"product_name\" from downloader_history where \"satellite_id\"={} and \"site_id\"={}".format(satelliteId, currentAOI.siteId))
                        self.cursor.execute("""select \"product_name\" from downloader_history where satellite_id = %(sat_id)s :: smallint and
                                                                       site_id = %(site_id)s :: smallint and
                                                                       status_id != %(status_downloading)s :: smallint and 
                                                                       status_id != %(status_failed)s ::smallint """, {
                                                                           "sat_id" : satelliteId,
                                                                           "site_id" : currentAOI.siteId,
                                                                           "status_downloading" : DATABASE_DOWNLOADER_STATUS_DOWNLOADING_VALUE,
                                                                           "status_failed" : DATABASE_DOWNLOADER_STATUS_FAILED_VALUE
                                                                       })
                        if self.cursor.rowcount > 0:
                            result = self.cursor.fetchall()
                            for res in result:
                                if len(res) == 1:
                                    currentAOI.appendHistoryFile(res[0])
                        self.cursor.execute("select * from sp_get_site_tiles({} :: smallint, {})".format(currentAOI.siteId, satelliteId))
                        if self.cursor.rowcount > 0:
                            result = self.cursor.fetchall()
                            for res in result:
                                if len(res) == 1:
                                    currentAOI.appendTile(res[0])
                    except Exception, e:
                        print("exception = {}".format(e))
                        print("Error in getting the downloaded files")
                        dbHandler = False
                        self.databaseDisconnect()
                if dbHandler:
                    retArray.append(currentAOI)

        self.databaseDisconnect()
        return retArray

    def upsertProductHistory(self, siteId, satelliteId, productName, status, productDate, fullPath, maxRetries):
        if not self.databaseConnect():
            print("upsertProductHistory could not connect to DB")
            return False
        try:
            #see if the record does already exist in db
            self.cursor.execute("""SELECT id, status_id, no_of_retries FROM downloader_history 
                                WHERE site_id = %(site_id)s and
                                satellite_id = %(satellite_id)s and
                                product_name = %(product_name)s""", 
                                {
                                    "site_id" : siteId, 
                                    "satellite_id" : satelliteId,
                                    "product_name" : productName
                                })
            rows = self.cursor.fetchall()
            if len(rows) > 1:
                print("upsertProductHistory error: the select for product {} retuirned more than 1 entry. Illegal, should be only 1 entry in downloader_history table".format(productName))
                self.databaseDisconnect()
                return False
            if len(rows) == 0:
                #if it doesn't exist, simply insert it with the provided info
                self.cursor.execute("""INSERT INTO downloader_history (site_id, satellite_id, product_name, full_path, status_id, no_of_retries, product_date) VALUES (
                                    %(site_id)s :: smallint, 
                                    %(satellite_id)s :: smallint,
                                    %(product_name)s, 
                                    %(full_path)s,
                                    %(status_id)s :: smallint,
                                    %(no_of_retries)s :: smallint,
                                    %(product_date)s :: timestamp)""", 
                                    {
                                        "site_id" : siteId, 
                                        "satellite_id" : satelliteId, 
                                        "product_name" : productName, 
                                        "full_path" : fullPath,
                                        "status_id" : status,
                                        "no_of_retries" : 1,
                                        "product_date" : productDate
                                    })
            else:
                #if the record for this product name does exist, act accordingly the provided status
                if len(rows[0]) != 3:
                    print("DB result has more than 3 fields !")
                    self.databaseDisconnect()
                    return False
                db_l1c_id = rows[0][0]
                db_status_id = rows[0][1]
                db_no_of_retries = rows[0][2]
                #for the following values, only the status will be updated
                if status == DATABASE_DOWNLOADER_STATUS_DOWNLOADING_VALUE or \
                status == DATABASE_DOWNLOADER_STATUS_DOWNLOADED_VALUE or \
                status == DATABASE_DOWNLOADER_STATUS_PROCESSED_VALUE or \
                status == DATABASE_DOWNLOADER_STATUS_ABORTED_VALUE:
                    self.cursor.execute("""UPDATE downloader_history SET status_id = %(status_id)s :: smallint 
                                        WHERE id = %(l1c_id)s :: smallint """, 
                                        {
                                            "status_id" : status,
                                            "l1c_id" : db_l1c_id
                                        })
                #if the failed status is provided , update it in the table if the no_of_retries 
                #does not exceed maxRetries, otherwise set the status as aborted and forget about it
                elif status == DATABASE_DOWNLOADER_STATUS_FAILED_VALUE:
                    if db_no_of_retries >= maxRetries:
                        status = DATABASE_DOWNLOADER_STATUS_ABORTED_VALUE
                    else:
                        db_no_of_retries += 1
                    self.cursor.execute("""UPDATE downloader_history SET status_id = %(status_id)s :: smallint , no_of_retries = %(no_of_retries)s :: smallint
                                        WHERE id = %(l1c_id)s :: smallint """, 
                                        {
                                            "status_id" : status,
                                            "no_of_retries" : db_no_of_retries,
                                            "l1c_id" : db_l1c_id
                                        })
                else:
                    self.databaseDisconnect()
                    print("The provided status {} is not one of the known status from DB. Check downloader_status table !".format(status))
                    return False
            self.conn.commit()
        except:
            print("The query for product {} raised an exception !".format(productName))
            self.databaseDisconnect()
            return False
        self.databaseDisconnect()
        return True


    def updateHistory(self, siteId, satelliteId, productName, productDate, fullPath):
        if not self.databaseConnect():
            return False
        try:
            print("UPDATING: insert into downloader_history (\"site_id\", \"satellite_id\", \"product_name\", \"product_date\", \"full_path\") VALUES ({}, {}, '{}', '{}', '{}')".format(siteId, satelliteId, productName, productDate, fullPath))
            self.cursor.execute("""insert into downloader_history (site_id, satellite_id, product_name, product_date, full_path) VALUES (
                                    %(site_id)s :: smallint, 
                                    %(satellite_id)s :: smallint, 
                                    %(product_name)s, 
                                    %(product_date)s :: timestamp,
                                    %(full_path)s)""", {
                                        "site_id" : siteId, 
                                        "satellite_id" : satelliteId, 
                                        "product_name" : productName, 
                                        "product_date": productDate,
                                        "full_path" : fullPath
                                    })
            self.conn.commit()
        except:
            print("DATABASE INSERT query FAILED!!!!!")
            self.databaseDisconnect()
            return False
        self.databaseDisconnect()
        return True


###########################################################################
class SentinelAOIInfo(AOIInfo):
    def __init__(self, serverIP, databaseName, user, password, logFile=None):
        AOIInfo.__init__(self, serverIP, databaseName, user, password, logFile)

    def getSentinelAOI(self):
        return self.getAOI(SENTINEL2_SATELLITE_ID)

    #def updateSentinelHistory(self, siteId, productName, productDate, fullPath):
    #    return self.updateHistory(siteId, SENTINEL2_SATELLITE_ID, productName, productDate, fullPath)

    def upsertSentinelProductHistory(self, siteId, productName, status, productDate, fullPath = "", maxRetries = 0):
        return self.upsertProductHistory(siteId, SENTINEL2_SATELLITE_ID, productName, status, productDate, fullPath, maxRetries)


###########################################################################
class LandsatAOIInfo(AOIInfo):
    def __init__(self, serverIP, databaseName, user, password, logFile=None):
        AOIInfo.__init__(self, serverIP, databaseName, user, password, logFile)

    def getLandsatAOI(self):
        return self.getAOI(LANDSAT8_SATELLITE_ID)

    #def updateLandsatHistory(self, siteId, productName, productDate, fullPath):
    #    return self.updateHistory(siteId, LANDSAT8_SATELLITE_ID, productName, productDate, fullPat)h

    def upsertLandsatProductHistory(self, siteId, productName, status, productDate, fullPath = "", maxRetries = 0):
        return self.upsertProductHistory(siteId, LANDSAT8_SATELLITE_ID, productName, status, productDate, fullPath, maxRetries)


###########################################################################
class DEMMACCSConfig(object):
    def __init__(self, output_path, gips_path, srtm_path, swbd_path, maccs_ip_address, maccs_launcher, working_dir):
        self.output_path = output_path
        self.gips_path = gips_path
        self.srtm_path = srtm_path
        self.swbd_path = swbd_path
        self.maccs_ip_address = maccs_ip_address
        self.maccs_launcher = maccs_launcher
        self.working_dir = working_dir


###########################################################################
class L1CInfo(object):
    def __init__(self, server_ip, database_name, user, password, log_file=None):
        self.server_ip = server_ip
        self.database_name = database_name
        self.user = user
        self.password = password
        self.is_connected = False;
        self.log_file = log_file

    def database_connect(self):
        if self.is_connected:
            return True
        connectString = "dbname='{}' user='{}' host='{}' password='{}'".format(self.database_name, self.user, self.server_ip, self.password)
        print("connectString:={}".format(connectString))
        try:
            self.conn = psycopg2.connect(connectString)
            self.cursor = self.conn.cursor()
            self.is_connected = True
        except:
            print("Unable to connect to the database")
            exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
            # Exit the script and print an error telling what happened.
            print("Database connection failed!\n ->{}".format(exceptionValue))
            self.is_connected = False
            return False
        return True

    def database_disconnect(self):
        if self.conn:
            self.conn.close()
            self.is_connected = False

    def get_demmaccs_config(self):
        if not self.database_connect():
            print("1")
            return None
        try:
            self.cursor.execute("select * from sp_get_parameters('demmaccs')")
            rows = self.cursor.fetchall()
        except:
            self.database_disconnect()
            return None
        output_path = ""
        gips_path = ""
        srtm_path = ""
        swbd_path = ""
        maccs_ip_address = ""
        maccs_launcher = ""
        working_dir = ""

        for row in rows:
            if len(row) != 3:
                continue
            if row[0] == DATABASE_DEMMACCS_OUTPUT_PATH:
                output_path = row[2]
            if row[0] == DATABASE_DEMMACCS_GIPS_PATH:
                gips_path = row[2]
            elif row[0] == DATABASE_DEMMACCS_SRTM_PATH:
                srtm_path = row[2]
            elif row[0] == DATABASE_DEMMACCS_SWBD_PATH:
                swbd_path = row[2]
            elif row[0] == DATABASE_DEMMACCS_MACCS_IP_ADDRESS:
                maccs_ip_address = row[2]
            elif row[0] == DATABASE_DEMMACCS_MACCS_LAUNCHER:
                maccs_launcher = row[2]
            elif row[0] == DATABASE_DEMMACCS_WORKING_DIR:
                working_dir = row[2]

        self.database_disconnect()
        if len(output_path) == 0 or len(gips_path) == 0 or len(srtm_path) == 0 or len(swbd_path) == 0 or len(maccs_ip_address) == 0 or len(maccs_launcher) == 0 or len(working_dir) == 0:
            print("{} {} {} {} {} {} {} {} {}".format(len(output_path), len(gips_path), len(srtm_path), len(swbd_path), len(maccs_ip_address), len(maccs_launcher), len(working_dir)))
            return None
        return DEMMACCSConfig(output_path, gips_path, srtm_path, swbd_path, maccs_ip_address, maccs_launcher, working_dir)

    def get_short_name(self, table, use_id):
        if not self.database_connect():
            return ""
        if table != "site" and table != "processor":
            return ""
        try:
            self.cursor.execute("select short_name from {} where id={}".format(table, use_id))
            rows = self.cursor.fetchall()
        except:
            self.database_disconnect()
            return ""
        self.database_disconnect()
        return rows[0][0]

    # will return a list with lists for each unique pair (satellite_id, site_id)
    def get_unprocessed_l1c(self):
        if not self.database_connect():
            return []
        try:
            self.cursor.execute("select id from satellite")
            satellite_ids = self.cursor.fetchall()
            if len(satellite_ids) != 1 and len(satellite_ids[0]) == 0:
                print("No satellite ids found in satellite table")
                return []
            #print("----{}".format(satellite_ids))
            self.cursor.execute("select id from site")
            site_ids = self.cursor.fetchall()
            if len(site_ids) != 1 and len(site_ids[0]) == 0:
                print("No site ids found in satellite table")
                return []
            retArray = []
            for satellite_id in satellite_ids:
                for site_id in site_ids:          
                    self.cursor.execute("""SELECT id, site_id, satellite_id, full_path, product_date FROM downloader_history WHERE 
                                        satellite_id = %(satellite_id)s :: smallint and 
                                        site_id = %(site_id)s  :: smallint and
                                        status_id = %(status_id)s :: smallint ORDER BY product_date ASC""", 
                                        {
                                            "satellite_id" : satellite_id[0],
                                            "status_id" : DATABASE_DOWNLOADER_STATUS_DOWNLOADED_VALUE,
                                            "site_id" : site_id[0]
                                        })
                    rows = self.cursor.fetchall()
                    if len(rows) > 0:
                        retArray.append(rows)
        except:
            print("!!!!!!!!!!!!!!!")
            self.database_disconnect()
            return []
        self.database_disconnect()
        return retArray

    def get_previous_l2a_tile_path(self, satellite_id, tile_id, l1c_date):
        if not self.database_connect():
            return ""
        path = ""
        try:
            self.cursor.execute("""SELECT path FROM sp_get_last_l2a_product(%(tile_id)s, 
                                                                            %(satellite_id)s :: smallint, 
                                                                            %(l1c_date)s :: timestamp)""",
                                {
                                    "tile_id" : tile_id,
                                    "satellite_id" : satellite_id,
                                    "l1c_date" : l1c_date.strftime("%Y%m%dT%H%M%S")
                                })            
            rows = self.cursor.fetchall()            
            if len(rows) == 1:
                path = rows[0][0]
        except:
            print("Database query failed in get_previous_l2a_tile_path!!!!!")
            self.database_disconnect()
            return path
        self.database_disconnect()
        return path

    def set_processed_product(self, processor_id, site_id, l1c_id, l2a_processed_tiles, full_path, product_name, footprint, sat_id, acquisition_date):
        #input params:
        #l1c_id is the id for the found L1C product in the downloader_history table. It shall be marked as being processed
        #product type by default is 1
        #processor id
        #site id
        #job id has to be NULL
        #full path is the whole path to the product including the name
        #created timestamp NULL
        #name product (basename from the full path)
        #quicklook image has to be NULL
        #footprint
        if not self.database_connect():
            return False
        try:
            self.cursor.execute("""update downloader_history set status_id = %(status_id)s :: smallint where id=%(l1c_id)s :: smallint """, 
                                {
                                    "status_id" : DATABASE_DOWNLOADER_STATUS_PROCESSED_VALUE, 
                                    "l1c_id" : l1c_id
                                })
            if len(l2a_processed_tiles) > 0:
                self.cursor.execute("""select * from sp_insert_product(%(product_type_id)s :: smallint,
                               %(processor_id)s :: smallint, 
                               %(satellite_id)s :: smallint, 
                               %(site_id)s :: smallint, 
                               %(job_id)s :: smallint, 
                               %(full_path)s :: character varying,
                               %(created_timestamp)s :: timestamp,
                               %(name)s :: character varying,
                               %(quicklook_image)s :: character varying,
                               %(footprint)s,
                               %(tiles)s :: json)""",
                                {
                                    "product_type_id" : 1,
                                    "processor_id" : processor_id,
                                    "satellite_id" : sat_id,
                                    "site_id" : site_id,
                                    "job_id" : None,
                                    "full_path" : full_path,
                                    "created_timestamp" : acquisition_date,
                                    "name" : product_name,
                                    "quicklook_image" : "mosaic.jpg",
                                    "footprint" : footprint, 
                                    "tiles" : '[' + ', '.join(['"' + t + '"' for t in l2a_processed_tiles]) + ']' 
                                })
            self.conn.commit()
        except Exception, e:
            print("Database update query failed: {}".format(e))            
            self.database_disconnect()
            return False
        self.database_disconnect()
        return True