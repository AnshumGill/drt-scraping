from io import BytesIO
from flask import Flask,request
from sqlalchemy.exc import SQLAlchemyError,IntegrityError
from PIL import Image
from bs4 import BeautifulSoup
from requests import session,ConnectionError
from models import db,CaseReport,Applicant,Respondent
from constants import *
import pytesseract
import logging
import datetime
import re

pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"]="mysql+pymysql://root:password@drt_scrape_db:3306/drt"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]="True"
db.app=app
db.init_app(app)
db.create_all()

def get_captcha(s: session) -> str:
    resp_img=s.get(captchaUrl)
    img=Image.open(BytesIO(resp_img.content))
    captcha_val=pytesseract.image_to_string(img).strip()
    if(len(captcha_val)==0):
        raise TypeError("Captcha could not be resolved correctly.")
    return captcha_val

def getSchema(s:session,drtName:str) -> str:
    logging.info("Getting Schema Name from provided DRT Name")
    resp=s.get(url)
    if(resp.status_code==200):
        soup=BeautifulSoup(resp.content,'html5lib')
        schemaname=soup.find(name="option",text=re.compile(drtName))
        if(schemaname != None):
            return schemaname['value']
    return None

def getAddress(tag: BeautifulSoup) -> str:
    address=tag.find(text=re.compile(addressStrig)).text.strip().split(':')
    if(len(address)>1):
        return address[1].strip()
    else:
        logging.debug("Address not found")
        return None

def getAdvocate(tag: BeautifulSoup) -> str:
    adv=tag.find(text=re.compile(advString)).text.strip().split(':')
    if(len(adv)>1):
        return adv[1].strip()
    else:
        logging.debug("Advocate Name not found")
        return None

def processParty(row: BeautifulSoup,moreInfo: BeautifulSoup) -> str:
    logging.debug("Inserting Parties")
    cols=row.find_all(name="td")
    respondantMoreInfo=moreInfo.find(name='th',text=re.compile(respondentHeaderString)).parent.find_next_sibling('tr').find(name='td')
    respondent=Respondent(cols[col_map['respondent']].text.strip(),getAddress(respondantMoreInfo),getAdvocate(respondantMoreInfo))
    applicantMoreInfo=moreInfo.find(name='th',text=re.compile(applicantHeaderString)).parent.find_next_sibling('tr').find(name='td')
    applicant=Applicant(cols[col_map['applicant']].text.strip(),getAddress(applicantMoreInfo),getAdvocate(applicantMoreInfo))
    try:
        db.session.add_all([respondent,applicant])
        db.session.commit()
        logging.debug(f"Inserted {respondent.name} {applicant.name}")
        return True
    except IntegrityError as e:
        logging.error(f"Record already exists, {respondent.name} {applicant.name}")
        db.session.rollback()
        return False
    except SQLAlchemyError as e:
        logging.error(f"Error occurred while inserting record for party, {e}")
        return False
    
def processCases(row: BeautifulSoup,moreInfo: BeautifulSoup) -> str:
    cols=row.find_all(name="td")
    diary=cols[col_map['diary']].text.strip().split('/')[0]
    caseCol=cols[col_map['caseNo']].text.strip()
    logging.debug(f"Inserting case {caseCol}")
    if(caseCol != noCaseString):
        caseType=caseCol.split('/')[0]
        caseNum=caseCol.split('/')[1]
    else:
        caseType=defaultCaseString
        caseNum=defaultCaseString
    dateFiling=datetime.datetime.strptime(cols[col_map['dateFiling']].text.strip(),'%d/%m/%Y')
    respName=cols[col_map['respondent']].text.strip()
    appName=cols[col_map['applicant']].text.strip()
    nextDate,disposedDate,courtNo,courtOf=None,None,None,None
    try:
        status=moreInfo.find(name='td',text=re.compile(caseStatusString)).find_next_sibling('td').text.strip()
        if(status==pendingStatus):
            getNextDate=moreInfo.find(name='td',text=re.compile(nextDateString)).find_next_sibling('td').text.strip()
            nextDate=datetime.datetime.strptime(getNextDate,'%d/%m/%Y') if len(getNextDate) > 1 and len(getNextDate) <= 10 else None
            nextDate=datetime.datetime.strftime(nextDate,'%Y-%m-%d') if nextDate else None
            getCourtNo=moreInfo.find(name='td',text=re.compile(courtNoString)).find_next_sibling('td').text.strip()
            getCourtOf=moreInfo.find(name='td',text=re.compile(courtOfString)).find_next_sibling('td').text.strip()
            courtNo=getCourtNo if len(getCourtNo) >= 1 else None
            courtOf=getCourtOf if len(getCourtOf) > 1 else None
        elif(status==disposedStatus):
            getDisposedDate=moreInfo.find(name='td',text=re.compile(disposalString)).find_next_sibling('td').text.strip()
            disposedDate=datetime.datetime.strptime(getDisposedDate,'%d/%m/%Y') if len(getDisposedDate) > 1 else None
            disposedDate=datetime.datetime.strftime(disposedDate,'%Y-%m-%d') if disposedDate else None
    except AttributeError as e:
        logging.error(f"Attribute not found. Error occurred while inserting {diary} {caseType} {caseNum}")
        return False
    except ValueError as e:
        logging.error(f"Improper Values found. Error occurred while inserting information for {diary} {caseType} {caseNum}")
        return False
    case=CaseReport(diary,caseType,caseNum,datetime.datetime.strftime(dateFiling,'%Y-%m-%d'),respName,appName,status,nextDate,disposedDate,courtNo,courtOf)
    try:
        db.session.add(case)
        db.session.commit()
        logging.debug(f"Inserted {caseCol}")
        return True
    except IntegrityError as e:
        logging.error(f"Record already exists, {caseCol}")
        db.session.rollback()
        return False
    except SQLAlchemyError as e:
        logging.error(f"Error occurred while inserting record, {e}")
        return False

def getMoreInfoId(row: BeautifulSoup) -> str:
    aTag=row.find(name="a")
    logging.debug(f"Getting More Info Link ID for")
    if(aTag):
        href=aTag['href']
        moreInfoId=(href.split("'")[1])
        return moreInfoId
    else:
        logging.warning(f"Anchor tag not found for")
        return None

def requestMoreInfo(s:session,moreInfoId: BeautifulSoup) -> list:
    logging.debug(f"Requesting more info for {moreInfoId}")
    resp=s.get(moreInfoURL+moreInfoId)
    if(resp.status_code==200):
        moreSoup=BeautifulSoup(resp.content,'html5lib').find_all(name='tbody')
        return moreSoup
    else:
        logging.warning(f"Improper error code received when requesting more info for {moreInfoId}")
        return None

def processRows(s: session,table: BeautifulSoup) -> str: 
    logging.info("Starting processing of rows")     
    parties,cases=0,0
    for row in table.find_all(name="tr"):
        moreInfoId=getMoreInfoId(row)
        if(moreInfoId):
            moreSoup=requestMoreInfo(s,moreInfoId)
            if(processParty(row,moreSoup[1])):
                parties+=2
            if(processCases(row,moreSoup[0])):
                cases+=1
    return(f"{parties} Parties Processed. {cases} Cases Processed.")

@app.route('/scrape-cases',methods=["POST"])
def addInfo():
    drtName=request.json['drt_name']
    partyName=request.json['party_name']
    logging.info(f"Received DRT Name - {drtName} Party Name - {partyName}")
    with session() as s:
        try:
            schema=getSchema(s,drtName) 
            if(schema == None):
                logging.error(f"Schema was none for {drtName}")
                return (f"Given DRT Name could not be found. Please check and try again",500)
            captchaVal=get_captcha(s)
        except ConnectionError as e:
            logging.error(f"Cannot access URL {e}")
            return(f"URL not accessible. Please try again later",500)
        except TypeError as e:
            logging.error(f"Captcha resolution failed {e}")
            return(f"Captcha could not be resolved correctly",500)
        data = {
            'schemaname':schema,
            'name':partyName,
            'answer':captchaVal,
            'submit11':'Search'
        }
        resp=s.post(url,data=data)
        anotherSoup=BeautifulSoup(resp.content,'html5lib')
        table=anotherSoup.find(name="tbody")
        if(table):
            resp=processRows(s,table)
            logging.info(f"Request processed {resp}")
            return (f"Request processed successfully. {resp}",200)
        else:
            logging.error("<tbody> not found")
            return(f"Could not parse page",500)

if (__name__=="__main__"):
    app.run(debug=True,host="0.0.0.0",port=8080)
