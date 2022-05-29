from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '%(asctime)s %(levelname)s %(message)s',
    }},
    'handlers': {
    	'wsgi': {
	        'class': 'logging.StreamHandler',
	        'stream': 'ext://flask.logging.wsgi_errors_stream',
	        'formatter': 'default'
	    }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

captchaUrl="https://drt.gov.in/front/captcha.php"
url="https://drt.gov.in/front/page1_advocate.php"
moreInfoURL="https://drt.gov.in/drtlive/Misdetailreport.php?no="

col_map={
    'diary':0,
    'caseNo':1,
    'dateFiling':2,
    'applicant':3,
    'respondent':4
}

pendingStatus="Pending"
disposedStatus="Disposed"
addressStrig="Address"
advString="Advocate Name"
applicantHeaderString="PETITIONER/APPLICANT DETAIL"
respondentHeaderString="RESPONDENTS/DEFENDENT DETAILS"
noCaseString="Case Not Registered"
defaultCaseString="Not Registered"
caseStatusString="Case Status"
nextDateString="Next Listing Date"
courtNoString="Court No"
courtOfString="In the Court of"
disposalString="Date of Disposal"