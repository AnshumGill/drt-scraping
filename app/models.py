from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import NoReferenceError

db=SQLAlchemy()

class Respondent(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100),nullable=False)
    address=db.Column(db.String(500))
    advocate=db.Column(db.String(100))
    case=db.relationship('CaseReport',backref=db.backref('respondent',lazy=True))
    __table_args__=(UniqueConstraint('name','address',name='resp_uc'),)

    def __init__(self,name,address=None,advocate=None):
        self.name=name
        self.address=address
        self.advocate=advocate

class Applicant(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100),nullable=False)
    address=db.Column(db.String(500))
    advocate=db.Column(db.String(100))
    case=db.relationship('CaseReport',backref=db.backref('applicant',lazy=True))
    __table_args__=(UniqueConstraint('name','address',name='app_uc'),)

    def __init__(self,name,address=None,advocate=None):
        self.name=name
        self.address=address
        self.advocate=advocate


class CaseReport(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    diaryNumber=db.Column(db.Integer,nullable=False)
    caseType=db.Column(db.String(100),nullable=False)
    caseNumber=db.Column(db.String(100),nullable=False)
    dateFiling=db.Column(db.Date,nullable=False)
    respondentId=db.Column(db.Integer,db.ForeignKey('respondent.id'))
    applicantId=db.Column(db.Integer,db.ForeignKey('applicant.id'))
    status=db.Column(db.String(100))
    nextDate=db.Column(db.Date)
    disposedDate=db.Column(db.Date)
    courtNumber=db.Column(db.Integer)
    courtOf=db.Column(db.String(100))
    __table_args__=(UniqueConstraint('diaryNumber','caseType','caseNumber',name='case_uc'),)
    
    def __init__(self,
        diaryNumber,
        caseType,
        caseNumber,
        dateFiling,
        respondent,
        applicant,
        status=None,
        nextDate=None,
        disposedDate=None,
        courtNumber=None,
        courtOf=None):
        self.diaryNumber=diaryNumber
        self.caseType=caseType
        self.caseNumber=caseNumber
        self.dateFiling=dateFiling
        respObj=Respondent.query.filter_by(name=respondent).first()
        appObj=Applicant.query.filter_by(name=applicant).first()
        if(respObj == None or appObj == None):
            raise NoReferenceError("The Respondent/Applicant could not be found")
        else:
            self.respondentId=respObj.id
            self.applicantId=appObj.id
        self.status=status
        self.nextDate=nextDate
        self.disposedDate=disposedDate
        self.courtNumber=courtNumber
        self.courtOf=courtOf
        