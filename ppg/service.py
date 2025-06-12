import sys
from flask import Flask,request,jsonify,send_file,Response
from flask import Blueprint
from ppg import datastore as database
import uuid
from datetime import datetime,timedelta
import time
import hashlib
import base64
import secrets
import binascii
from functools import wraps
import json
from ppg.BP_Estimation_Models_Files import main as onnx_model
from ppg.fidelius import fidelius
import os
import subprocess
import shutil
import pandas as pd
from urllib.parse import unquote
import requests
from werkzeug.utils import secure_filename
from ppg.utils.app_utils import AppUtils
from ppg.auth import AuthHandler
from bson import ObjectId
from packaging import version
from dateutil.relativedelta import relativedelta

# PPG_MAIN_SERVER = "http://ec2-13-233-95-219.ap-south-1.compute.amazonaws.com:5000/service" #AWS Prod
# PPG_MAIN_SERVER = "http://ec2-65-0-182-165.ap-south-1.compute.amazonaws.com:5001/service"
PPG_MAIN_SERVER = "http://ec2-65-0-182-165.ap-south-1.compute.amazonaws.com:5000/service"#compute_stage_2.0
service_url = Blueprint('service_url', __name__)

@service_url.route("/")
def home():
	return "Successfully runnig!"

#function to validate request
def account(param):
	@wraps(param)
	def account(*args, **kwargs):
		if validate_bearer_token(request):
			return validate_bearer_token(request)
		else:
			pass
		return param(*args, **kwargs)

	return account

#create_patient_profile
@service_url.route("/create/patient/profile", methods=['POST'])
# @account
def create_patient_profile():
	try:
		input_json = request.get_json(force=True)
		if input_json['demographics']:
			create_data=database.create_patient_demographics(input_json['demographics'])
		else:
			return jsonify({"success":0,"message":"unable to create"})
		return jsonify({"success":1,"message":"demographics created successfully"})

	except Exception as e:
		print("e1:",e)
		return jsonify({"success":0,"message":"unable to create"})

def generate_mr_number():
	try:
		last_mr = database.last_patient_mr()
		if last_mr == None:
			new_mr_number = 'MR1'
		else:
			last_mr_number = int(last_mr[2:])
			new_mr_number = 'MR'+str(last_mr_number+1)
		check_mr = database.check_patient_mr(new_mr_number)
		if check_mr == 1:
			new_mr_status=0
			while(new_mr_status==0):
				current_mr_number = int(new_mr_number[2:])
				new_mr_number = 'MR'+str(current_mr_number+1)
				check_mr = database.check_patient_mr(new_mr_number)
				if check_mr == 1:
					continue
				else:
					new_mr_status=1
					break
		else:
			pass
		return new_mr_number
	except Exception as e:
		print("eeee:",e)
		return None

#get_patient_profile
@service_url.route("/get/patient/profile", methods=['GET'])
@account
def get_patient_profile():
	try:
		uhid=request.args.get('uhid',None)
		phone_number=request.args.get('phone_number',None)
		mr_number=request.args.get('mr_number',None)
		user_name=request.args.get('user_name',None)
		if user_name != None:
			user_name=unquote(user_name)


		# if uhid != None:
		# 	uhid =encrypt_raw_data(uhid)#input_json['uhid'] #uhid encryption
		# if phone_number != None:
		# 	phone_number=encrypt_raw_data(phone_number)#input_json['phone_number']
		# if mr_number != None:
		# 	mr_number=encrypt_raw_data(mr_number)#input_json['phone_number']
		# if user_name != None:
		# 	user_name=encrypt_raw_data(user_name)#input_json['phone_number']

		get_profile=database.get_patient_demographics(uhid,phone_number,mr_number,user_name)
		# get_profile = [decrypt_raw_data(get_profile[0])] #decrypt already encrypted data

		uhid=get_profile[0]['uhid']

		try:
			if 'chief_complaint' not in get_profile[0]:
				get_profile[0]['chief_complaint']=""

			if 'address' not in get_profile[0]:
				get_profile[0]['address']=""

			if 'ethnicity' not in get_profile[0]:
				get_profile[0]['ethnicity']=""

			if 'country_code' not in get_profile[0]:
				get_profile[0]['country_code']=""

			if 'notes' not in get_profile[0]:
				get_profile[0]['notes']=""

		except :
			pass

		try:
			uhid=get_profile[0]['uhid']
			health_data=get_patienthealth_record(uhid)
			get_profile[0]['health_status']=health_data[0]['health_status']
		except Exception as e:
			print("e:",e)
			get_profile[0]['health_status']=""
			pass

		try:
			vital_data = database.get_patient_vitals(uhid)[0]
			if 'wrist_size' not in vital_data:
				vital_data['wrist_size']=""

			if 'bp_dia2' not in vital_data:
				vital_data['bp_dia2']=""

			if 'bp_sys2' not in vital_data:
				vital_data['bp_sys2']=""

			if 'bp2' not in vital_data:
				vital_data['bp2']=""
				
			get_profile[0]['vital_details'] = vital_data
		except Exception as e:
			get_profile[0]['vital_details']={}

		try:
			health_record=get_patienthealth_record(uhid)
			get_profile[0]['health_record']=health_record[0]
			get_profile[0]['observation_per_visit']=health_record[0]['get_patienthealth_record']
		except Exception as e:
			get_profile[0]['health_record']={}
			get_profile[0]['observation_per_visit']=3
		try:
			site_details=database.get_patient_sitedetails(get_profile[0]['id'])
			get_profile[0]['operator_name']=site_details[0]['operator_name']
			get_profile[0]['device_details']=site_details[0]['device_details']
			get_profile[0]['device_address']=site_details[0]['device_address']
			get_profile[0]['device_brand']=site_details[0]['device_brand']
			get_profile[0]['site_name']=site_details[0]['site_name']
		except Exception as e:
			print("e:",e)
			pass

		try:
			get_profile[0]['calibration_overall_status']=getpatient_calibration(uhid)[0]['calibration_overall_status']
		except Exception as e:
			print("e:",e)
			get_profile[0]['calibration_overall_status']=False
			pass

		return jsonify({"success":1,"message":get_profile})
	except Exception as e:
		print("e2:",e)
		return jsonify({"success":0,"message":"unable to get"})


#get_patient_profile by name search
@service_url.route("/get/patient/namesearch", methods=['GET'])
@account
def get_patient_name_search():
	try:
		uhid=request.args.get('uhid',None)
		user_name=request.args.get('user_name',None)
		phone_number=request.args.get('phone_number',None)
		mr_number=request.args.get('mr_number',None)

		# if uhid != None:
		# 	uhid =encrypt_raw_data(uhid)#input_json['uhid'] #uhid encryption
		# if phone_number != None:
		# 	phone_number=encrypt_raw_data(phone_number)#input_json['phone_number']
		# if mr_number != None:
		# 	mr_number=encrypt_raw_data(mr_number)#input_json['phone_number']
		# if user_name != None:
		# 	user_name=encrypt_raw_data(user_name)#input_json['phone_number']

		get_profile=database.get_patient_demographics(uhid,phone_number,mr_number,user_name)

		for i in get_profile:
			# i = decrypt_raw_data(i) #decrypt already encrypted data
			uhid=i['uhid']

			try:
				health_data=get_patienthealth_record(uhid)
				i['health_status']=health_data[0]['health_status']
			except Exception as e:
				print("e:",e)
				i['health_status']=""
				pass

			try:
				vital_data = database.get_patient_vitals(uhid)[0]
				i['vital_details'] = vital_data
			except Exception as e:
				i['vital_details']={}

			try:
				health_record=get_patienthealth_record(uhid)
				i['health_record']=health_record[0]
				get_profile[0]['observation_per_visit']=health_record[0]['get_patienthealth_record']
			except Exception as e:
				i['health_record']={}
				get_profile[0]['observation_per_visit']= 3
			try:
				site_details=database.get_patient_sitedetails(i['id'])
				i['operator_name']=site_details[0]['operator_name']
				i['device_details']=site_details[0]['device_details']
				i['device_address']=site_details[0]['device_address']
				i['device_brand']=site_details[0]['device_brand']
				i['site_name']=site_details[0]['site_name']
			except Exception as e:
				print("e:",e)
				pass

			try:
				i['calibration_overall_status']=getpatient_calibration(uhid)[0]['calibration_overall_status']
			except Exception as e:
				print("e:",e)
				i['calibration_overall_status']=False
				pass
				
		return jsonify({"success":1,"message":get_profile})
	except Exception as e:
		print("e2:",e)
		return jsonify({"success":0,"message":"unable to get"})


#update_patient_profile
@service_url.route("/update/patient/profile", methods=['POST'])
# @account
def update_patient_profile():
	try:
		input_json = request.get_json(force=True)
		current_time = datetime.now()

		if 'address' not in input_json:
			input_json['address']=""

		if 'ethnicity' not in input_json:
			input_json['ethnicity']=""

		if 'country_code' not in input_json:
			input_json['country_code']=""

		if 'notes' not in input_json:
			input_json['notes']=""

		# input_data={"id":input_json['id'], "modified_at":current_time, "first_name": input_json['first_name'],"last_name": input_json['last_name'], "phone_number": input_json['phone_number'],"email": input_json['email'],"avatar": input_json['avatar'], "gender":(input_json['gender']).lower(),"dob":input_json['dob'],"age_in_days":input_json['age_in_days'],"user_name": input_json['user_name'],"age":input_json['age'],"mr_number":input_json['mr_number'],"address":input_json['address'],"ethnicity":input_json['ethnicity'],"country_code":input_json['country_code'],"notes":input_json['notes']}

		# input_data=encrypt_raw_data(input_data) #uhid encryption
		update_data=database.update_patient_demographics(input_json)

		if update_data==0:
			return jsonify({"success":0,"message":"record not exist"})

		return jsonify({"success":1,"message":"updated successfully"})
	except Exception as e:
		print("e3:",e)
		return jsonify({"success":0,"message":"unable to update"})

#update_patient_all type of heath records
@service_url.route("/update/patient/health/record", methods=['POST'])
# @account
def update_patient_health_record():
	try:
		input_json = request.get_json(force=True)
		health_json = input_json['health_record']
		demo_json = input_json['demographics']
		if 'chief_complaint' not in health_json:
			health_json['chief_complaint']=""
		if 'notes' not in health_json:
			health_json['notes']=""
		if 'observation_per_visit' not in health_json:
			health_json['observation_per_visit']=3
		if database.check_patient_healthrecord(health_json['uhid']) == 1:
			
			update_data=database.update_patient_healthrecord(health_json)
		else:
			return jsonify({"success":0,"message":"record not exist"})

		if update_data==0:
			return jsonify({"success":0,"message":"record not exist"})

		return jsonify({"success":1,"message":"updated successfully"})
	except Exception as e:
		print("e3:",e)
		return jsonify({"success":0,"message":"unable to update"})


#get_patient_profile
@service_url.route("/get/patient/health/record", methods=['GET'])
@account
def get_patient_health_record():
	try:
		uhid=request.args.get('uhid',None)
		get_profile=get_patienthealth_record(uhid)
		vital_data = database.get_patient_vitals(uhid)
		get_profile[0]['vital_details'] = vital_data
		return jsonify({"success":1,"message":get_profile})
	except Exception as e:
		print("e2:",e)
		return jsonify({"success":0,"message":"unable to get"})

#get_patient_profile
def get_patienthealth_record(uhid):
	try:
		# uhid=request.args.get('uhid')
		get_profile=database.get_patient_healthrecord(uhid)
		return get_profile
	except Exception as e:
		print("e2:",e)
		return "unable to get"

#create_operator_profile
@service_url.route("/create/operator/profile", methods=['POST'])
@account
def create_operator_profile():
	print("innn")
	try:
		print("try")
		input_json = request.get_json(force=True)
		current_time = datetime.now()

		if 'phone_number' not in input_json:
			return jsonify({'success' : 0, 'message' : 'phone_number is missing'})

		if 'user_name' not in input_json:
			return jsonify({'success' : 0, 'message' : 'user_name is missing'})

		if database.check_operator_demographics((input_json['user_name']).lower(),None) ==1:
			return jsonify({'success' : 0, 'message' : 'user_name already exist'})

		try:
			input_json['user_type']
		except:
			input_json['user_type'] = 'operator'


		input_data={"id":str(uuid.uuid4()), "created_at":current_time, "modified_at":current_time, "first_name": input_json['first_name'],"last_name": input_json['last_name'],"user_name": (input_json['user_name']).lower(), "phone_number": input_json['phone_number'],"email": input_json['email'], "avatar": input_json['avatar'], "department": input_json['department'], "gender":(input_json['gender']).lower(),"dob":input_json['dob'],"is_active":True,"user_type":(input_json['user_type']).lower()}

		create_profile=database.create_operator_demographics(input_data)

		password=encode_md5(input_json['password'])

		credentials_detils={"id":str(uuid.uuid4()), "created_at":current_time, "modified_at":current_time, "operator_profile_id":input_data['id'], "user_name":(input_json['user_name']).lower(), "password":password }

		store_credentials = database.store_operator_credentials(credentials_detils)

		profile_data = {"id":str(input_data['id']),"phone_number":str(input_json['phone_number']),"user_name":(input_json['user_name']).lower(),"user_type":(input_json['user_type']).lower()}

		try:

			input_data2 = {"id":str(uuid.uuid4()), "created_at":current_time, "modified_at":current_time,"operator_profile_id":input_data['id'], "device_details":input_json['device_details'], "device_address":input_json['device_address'], "device_brand":input_json['device_brand'],"site_name":input_json['site_name'],"is_active":True}

			if database.check_operator_sitedetails(input_data['id'])==0:
				create_site_details=database.create_operator_sitedetails(input_data2)

		except Exception as e:
			print("ee:",e)
			pass
		try:
			final_json ={"demographics":input_data,"credentials":credentials_detils,"sitedetails":input_data2}
			url = PPG_MAIN_SERVER + "/create/operator/profile/trail"
			headers = {
			'Content-Type': 'application/json'
			}
			if 'created_at' in input_data:
				input_data['created_at']=str(input_data['created_at'])
			if 'modified_at' in input_data:
				input_data['modified_at']=str(input_data['modified_at'])
			if 'created_at' in input_data2:
				input_data2['created_at']=str(input_data2['created_at'])
			if 'modified_at' in input_data2:
				input_data2['modified_at']=str(input_data2['modified_at'])
			if 'created_at' in credentials_detils:
				credentials_detils['created_at']=str(credentials_detils['created_at'])
			if 'modified_at' in credentials_detils:
				credentials_detils['modified_at']=str(credentials_detils['modified_at'])


			if '_id' in input_data:
				del(input_data['_id'])
			if '_id' in input_data2:
				del(input_data2['_id'])
			if '_id' in credentials_detils:
				del(credentials_detils['_id'])
			response = requests.post(url, headers=headers, json=final_json)
			print("Response:", response.status_code, response.text)
			print(url,headers,final_json)
			print("response:",response)
			# return response
		except Exception as e:
			print("eee:",e)
		return jsonify({'success' : 1, 'message' : profile_data})

	except Exception as e:
		print("e4:",e)
		return jsonify({"success":0,"message":"unable to create"})

#convert str password into md5 encode
def encode_md5(password):
    try:
        md5_hash = hashlib.md5()
        md5_hash.update(str(password).encode('utf-8'))
        md5_password = md5_hash.hexdigest()
        return md5_password
    except Exception as e:
        return 0

#get_operator_profile
@service_url.route("/get/operator/profile", methods=['GET'])
@account
def get_operator_profile():
	try:
		user_name=request.args.get('user_name',None)
		phone_number=request.args.get('phone_number',None)
		get_profile=database.get_operator_demographics(user_name.lower(),phone_number)

		try:
			get_calibration=database.get_operator_sitedetails(get_profile[0]['id'])
			get_profile[0].update({"device_details":get_calibration[0]['device_details'],"device_address":get_calibration[0]['device_address'],"device_brand":get_calibration[0]['device_brand'],"site_name":get_calibration[0]['site_name']})
		except Exception as e:
			print("ee:",e)
			pass

		return jsonify({"success":1,"message":get_profile})
	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to get"})

#update_operator_profile
@service_url.route("/update/operator/profile", methods=['POST'])
@account
def update_operator_profile():
	try:
		input_json = request.get_json(force=True)
		current_time = datetime.now()

		input_data={"id":input_json['id'], "modified_at":current_time, "first_name": input_json['first_name'],"last_name": input_json['last_name'],"user_name":(input_json['old_user_name']).lower(), "phone_number": input_json['phone_number'],"email": input_json['email'], "avatar": input_json['avatar'], "department": input_json['department'], "gender":(input_json['gender']).lower(),"dob":input_json['dob'],"user_type":(input_json['user_type']).lower()}

		update_data=database.update_operator_demographics(input_data)

		try:

			input_data2={"modified_at":current_time,"operator_profile_id":input_data['id'], "device_details":input_json['device_details'], "device_address":input_json['device_address'], "device_brand":input_json['device_brand'],"site_name":input_json['site_name']}

			update_sitedata=database.update_operator_sitedetails(input_data2)
		except Exception as e:
			print("ee:",e)
			pass

		try:
			current_time = datetime.now()
			if int(database.check_operator_demographics((input_json['old_user_name']).lower(),None)) ==0:
				return jsonify({'success' : 0, 'message' : 'old user name not exist'})

			input_data3={"id":input_json['id'], "modified_at":current_time, "new_user_name":(input_json['new_user_name']).lower(),"old_user_name":(input_json['old_user_name']).lower()}

			update_data=database.update_operator_profileusername(input_data3)
			if update_data==0:
				return jsonify({"success":0,"message":"record not exist"})

			update_name=database.update_operator_name(input_data3)
			if update_name==0:
				return jsonify({"success":0,"message":"record not exist"})

		except Exception as e:
			pass
		try:
			final_json ={"demographics":input_data,"profile":input_data3,"sitedetails":input_data2}
			url = PPG_MAIN_SERVER + "/update/operator/profile/trail"
			headers = {
			'Content-Type': 'application/json'
			}
			if 'created_at' in input_data:
				input_data['created_at']=str(input_data['created_at'])
			if 'modified_at' in input_data:
				input_data['modified_at']=str(input_data['modified_at'])
			if 'created_at' in input_data2:
				input_data2['created_at']=str(input_data2['created_at'])
			if 'modified_at' in input_data2:
				input_data2['modified_at']=str(input_data2['modified_at'])
			if 'created_at' in input_data3:
				input_data3['created_at']=str(input_data3['created_at'])
			if 'modified_at' in input_data3:
				input_data3['modified_at']=str(input_data3['modified_at'])


			if '_id' in input_data:
				del(input_data['_id'])
			if '_id' in input_data2:
				del(input_data2['_id'])
			if '_id' in input_data3:
				del(input_data3['_id'])
			response = requests.request("POST", url, headers=headers, json=final_json)
			print("response:",response)
			# return response
		except Exception as e:
			print("eee:",e)
		return jsonify({"success":1,"message":"updated successfully"})
	except Exception as e:
		print("e6:",e)
		return jsonify({"success":0,"message":"unable to update"})


#update operator site details
@service_url.route("/update/operator/site/details", methods=['POST'])
@account
def update_operator_site_details():
	try:
		input_json = request.get_json(force=True)
		current_time = datetime.now()

		input_data={"modified_at":current_time,"operator_profile_id":input_json['operator_id'], "device_details":input_json['device_details'], "device_address":input_json['device_address'], "device_brand":input_json['device_brand'],"site_name":input_json['site_name']}

		update_site=database.update_operator_sitedetails(input_data)
		try:
			url = PPG_MAIN_SERVER + "/update/operator/site/details/trail"
			headers = {
			'Content-Type': 'application/json'
			}
			if 'created_at' in input_data:
				input_data['created_at']=str(input_data['created_at'])
			if 'modified_at' in input_data:
				input_data['modified_at']=str(input_data['modified_at'])

			if '_id' in input_data:
				del(input_data['_id'])
			response = requests.request("POST", url, headers=headers, json=input_data)
			print("response:",response)
			# return response
		except Exception as e:
			print("eee:",e)
		return jsonify({"success":1,"message":"updated successfully"})
	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to get"})


#update operator site details
@service_url.route("/update/patient/site/details", methods=['POST'])
# @account
def update_patient_site_details():
	try:
		input_json = request.get_json(force=True)
		current_time = datetime.now()

		input_data=input_json['patient_sitedetails']

		update_site=database.update_patient_sitedetails(input_data)

		return jsonify({"success":1,"message":"updated successfully"})
	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to get"})


#update_operator_profile
@service_url.route("/update/operator/username", methods=['POST'])
@account
def update_operator_username():
	try:
		input_json = request.get_json(force=True)
		current_time = datetime.now()

		if int(database.check_operator_demographics((input_json['old_user_name']).lower(),None)) ==0:
			return jsonify({'success' : 0, 'message' : 'user not exist'})

		input_data={"id":input_json['id'], "modified_at":current_time, "new_user_name":(input_json['new_user_name']).lower(),"old_user_name":(input_json['old_user_name']).lower()}

		update_data=database.update_operator_profileusername(input_data)
		if update_data==0:
			return jsonify({"success":0,"message":"record not exist"})

		update_name=database.update_operator_name(input_data)
		if update_name==0:
			return jsonify({"success":0,"message":"record not exist"})
		try:
			url = PPG_MAIN_SERVER + "/update/operator/username/trail"
			headers = {
			'Content-Type': 'application/json'
			}
			if 'created_at' in input_data:
				input_data['created_at']=str(input_data['created_at'])
			if 'modified_at' in input_data:
				input_data['modified_at']=str(input_data['modified_at'])


			if '_id' in input_data:
				del(input_data['_id'])
			response = requests.request("POST", url, headers=headers, json=input_data)
			print("response:",response)
			# return response
		except Exception as e:
			print("eee:",e)
		return jsonify({"success":1,"message":"updated successfully"})
	except Exception as e:
		print("e7:",e)
		return jsonify({"success":0,"message":"unable to update"})

#validate_operator_profile
@service_url.route("/validate/operator/profile", methods=['POST'])
@account
def validate_operator_profile():
	try:
		input_json = request.get_json(force=True)

		phone_number = None
		if int(database.check_operator_demographics((input_json['user_name']).lower(),phone_number)) ==0:
			return jsonify({'success' : 0, 'message' : 'user not exist'})

		password=encode_md5(input_json['password'])
		if int(database.validate_operator_credentials((input_json['user_name']).lower(),password)) ==0:
			return jsonify({'success' : 0, 'message' : 'invalid credentials'})

		return jsonify({"success":1,"message":"validated successfully"})
	except Exception as e:
		print("e8:",e)
		return jsonify({"success":0,"message":"unable to validate"})

#login_operator_profile
@service_url.route("/login/operator/profile", methods=['POST'])
@account
def login_operator_profile():
	try:
		input_json = request.get_json(force=True)
		current_time = datetime.now()

		phone_number = None
		if int(database.check_operator_demographics((input_json['user_name']).lower(),phone_number)) ==0:
			return jsonify({'success' : 0, 'message' : 'user not exist'})

		password=encode_md5(input_json['password'])
		if int(database.validate_operator_credentials((input_json['user_name']).lower(),password)) ==0:
			return jsonify({'success' : 0, 'message' : 'invalid credentials'})

		get_profile=database.get_operator_demographics((input_json['user_name']).lower(),phone_number)
		unique_id = str(uuid.uuid4())
		input_data={"id":unique_id,"created_at":current_time,"modified_at":current_time,"login_time":str(current_time.time()),"login_date":str(current_time.date()),"operator_profile_id":get_profile[0]['id'],"user_name":(input_json['user_name']).lower(),"ip_address":input_json['ip_address'],"device_details":input_json['device_details'],"latitude":input_json['latitude'],"longitude":input_json['longitude'],"is_activte":True}
		input_json['id'] = unique_id
		login_log = database.save_operator_login_details(input_data)
		
		try:
			get_site_data = database.get_operator_sitedetails(get_profile[0]['id'])

			result = {"first_name": get_profile[0]['first_name'],"last_name": get_profile[0]['last_name'],"user_name":(get_profile[0]['user_name']).lower(), "phone_number": get_profile[0]['phone_number'],"email": get_profile[0]['email'], "avatar": get_profile[0]['avatar'], "department": get_profile[0]['department'], "gender":(get_profile[0]['gender']).lower(),"dob":get_profile[0]['dob']}

			site_data={"device_details":get_site_data[0]['device_details'], "device_address":get_site_data[0]['device_address'], "device_brand":get_site_data[0]['device_brand'],"site_name":get_site_data[0]['site_name']}

			result.update(site_data)
		except Exception as e:
			print("e:",e)
			result={}
		try:
			url = PPG_MAIN_SERVER + "/login/operator/profile/trail"
			headers = {
			'Content-Type': 'application/json'
			}
			if 'created_at' in input_data:
				input_data['created_at']=str(input_data['created_at'])
			if 'modified_at' in input_data:
				input_data['modified_at']=str(input_data['modified_at'])


			if '_id' in input_data:
				del(input_data['_id'])
			result['password'] =password
			result_json = {"login_details":input_data,"demographics":result}
			print("result_json",result_json)
			response = requests.request("POST", url, headers=headers, json=result_json)
			print("response:",response.content)
			# return response
		except Exception as e:
			print("eee:",e)
		return jsonify({"success":1,"message":"loggedin successfully","data":result})
	except Exception as e:
		print("e9:",e)
		return jsonify({"success":0,"message":"unable to login","data":{}})



#create_patient_ calibration
@service_url.route("/create/patient/calibration", methods=['POST'])
# @account
def create_patient_calibration():
	try:
		input_json = request.get_json(force=True)
		if 'uhid' not in input_json:
			return jsonify({'success' : 0, 'message' : 'uhid is missing'})

		uhid = input_json['uhid']
		# uhid =encrypt_raw_data(input_json['uhid']) #uhid encryption

		check_profile=database.check_patient_demographics(uhid,None)

		if check_profile == 1:
			get_profile=database.get_patient_demographics(uhid,None,None,None)

			if database.check_patient_calibration(uhid)==1:
				print("here1")
				return jsonify({"success":1,"message":"already created"})


			# get_data = database.get_calibrationprotocol(0,None,input_json['calibration_protocol_id'])
			# calibration_list=get_data[0]['calibration']

			calibration_list=[
			{"patient_profile_id":get_profile[0]['id'], "posture":"sitting", "activity":"induced", "calibration_name":"Calibration 1"},
			{"patient_profile_id":get_profile[0]['id'], "posture":"sitting", "activity":"rest", "calibration_name":"Calibration 2"},
			{"patient_profile_id":get_profile[0]['id'], "posture":"supine", "activity":"induced", "calibration_name":"Calibration 3"},
			{"patient_profile_id":get_profile[0]['id'], "posture":"supine", "activity":"rest", "calibration_name":"Calibration 4"}]

			for i in calibration_list:
				current_data={"modified_at":input_json['modified_at'],"uhid":input_json['uhid'], "patient_profile_id":input_json['patient_profile_id'], "measured_date":input_json['measured_date'],"bp1":input_json['bp1'], "bp1_sys":input_json['bp1_sys'], "bp1_dia":input_json['bp1_dia'], "bp1_measured_date":input_json['bp1_measured_date'],"bp2":input_json['bp2'], "bp2_sys":input_json['bp2_sys'], "bp2_dia":input_json['bp2_dia'], "bp2_measured_date":input_json['bp2_measured_date'], "posture":(input_json['posture']).lower(), "activity":(input_json['activity']).lower(), "ppg1_file":input_json['ppg1_file'], "ppg2_file":input_json['ppg2_file'], "calibration_status":input_json['calibration_status']}
				current_data.update(i)
				create_data=database.create_patient_calibration_record(current_data)

			return jsonify({"success":1,"message":"created successfully"})
		else:
			return jsonify({"success":0,"message":"profile not exist for this uhid"})

	except Exception as e:
		print("e1:",e)
		return jsonify({"success":0,"message":"unable to create"})


#update_patient_ calibration
@service_url.route("/update/patient/calibration", methods=['POST'])
# @account
def update_patient_calibration():
	try:
		input_json = request.get_json(force=True)
		if 'uhid' not in input_json:
			return jsonify({'success' : 0, 'message' : 'uhid is missing'})

		current_time = datetime.now()

		uhid = input_json['uhid']
		# uhid =encrypt_raw_data(input_json['uhid']) #uhid encryption

		check_profile=database.check_patient_demographics(uhid,None)

		if check_profile == 1:
			get_profile=database.get_patient_demographics(uhid,None,None,None)

			check_data=database.check_patient_calibration_record(input_json)

			if check_data==1:

				# input_data={"modified_at":current_time,"uhid":input_json['uhid'], "patient_profile_id":get_profile[0]['id'], "measured_date":input_json['measured_date'],"bp1":input_json['bp1'], "bp1_sys":input_json['bp1_sys'], "bp1_dia":input_json['bp1_dia'], "bp1_measured_date":input_json['bp1_measured_date'],"bp2":input_json['bp2'], "bp2_sys":input_json['bp2_sys'], "bp2_dia":input_json['bp2_dia'], "bp2_measured_date":input_json['bp2_measured_date'], "posture":(input_json['posture']).lower(), "activity":(input_json['activity']).lower(), "ppg1_file":input_json['ppg1_file'], "ppg2_file":input_json['ppg2_file'], "calibration_status":True}

				update_data=database.update_patient_calibration_record(input_json)

				if update_data == 1:
					return jsonify({"success":1,"message":"updated successfully"})
				else:
					return jsonify({"success":1,"message":"calibration record not found"})

			else:
				return jsonify({"success":0,"message":"calibration not found"})

		else:
			return jsonify({"success":0,"message":"profile not exist for this uhid"})

	except Exception as e:
		print("e1:",e)
		return jsonify({"success":0,"message":"unable to update"})

#get_patient calibration 
@service_url.route("/get/patient/calibration", methods=['GET'])
# @account
def get_patient_calibration():
	try:
		uhid=request.args.get('uhid',None)
		get_calibration=getpatient_calibration(uhid)
		return jsonify({"success":1,"message":get_calibration})
	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to get"})

#get_patient calibration 
def getpatient_calibration(uhid):
	try:
		get_calibration=database.get_patient_calibration_record(uhid)
		calibration_count=0
		for i in get_calibration:
			if i['calibration_status']==True:
				calibration_count+=1
		if calibration_count == len(get_calibration):
			get_calibration[0]['calibration_overall_status']=True
		else:
			get_calibration[0]['calibration_overall_status']=False

		return get_calibration
	except Exception as e:
		print("e5:",e)
		return []


#create_patient_ vitals
@service_url.route("/create/patient/vitals", methods=['POST'])
# @account
def create_patient_vitals():
	print("vitals")
	try:
		print("there")
		input_json = request.get_json(force=True)
		print("input_json vitals",input_json)
		if 'uhid' not in input_json:
			return jsonify({'success' : 0, 'message' : 'uhid is missing'})

		uhid = input_json['uhid']
		# uhid =encrypt_raw_data(input_json['uhid']) #uhid encryption
		check_profile=database.check_patient_demographics(uhid,None)

		if check_profile == 1:
			get_profile=database.get_patient_demographics(uhid,None,None,None)

			if 'respiratory_rate' not in input_json:
				input_json['respiratory_rate']=""

			if 'wrist_size' not in input_json:
				input_json['wrist_size']=""

			if 'bp_dia2' not in input_json:
				input_json['bp_dia2']=""

			if 'bp_sys2' not in input_json:
				input_json['bp_sys2']=""

			if 'bp2' not in input_json:
				input_json['bp2']=""


			create_data=database.create_patientvitals(input_json)

			return jsonify({"success":1,"message":"created successfully"})
		else:
			return jsonify({"success":0,"message":"profile not exist for this uhid"})

	except Exception as e:
		print("e1:",e)
		return jsonify({"success":0,"message":"unable to create"})

#update_patient_ vitals
@service_url.route("/update/patient/vitals", methods=['POST'])
# @account
def update_patient_vitals():
	try:
		input_json = request.get_json(force=True)
		if 'uhid' not in input_json:
			return jsonify({'success' : 0, 'message' : 'uhid is missing'})

		if 'id' not in input_json:
			return jsonify({'success' : 0, 'message' : 'id is missing'})

		current_time = datetime.now()

		uhid = input_json['uhid']
		# uhid =encrypt_raw_data(input_json['uhid']) #uhid encryption
		check_profile=database.check_patient_demographics(uhid,None)

		if check_profile == 1:
			get_profile=database.get_patient_demographics(uhid,None,None,None)

			check_data=database.check_patient_vitals(input_json['uhid'])

			if check_data==1:

				if 'respiratory_rate' not in input_json:
					input_json['respiratory_rate']=""

				if 'wrist_size' not in input_json:
					input_json['wrist_size']=""

				if 'bp_dia2' not in input_json:
					input_json['bp_dia2']=""

				if 'bp_sys2' not in input_json:
					input_json['bp_sys2']=""

				if 'bp2' not in input_json:
					input_json['bp2']=""

				# input_data={"id":input_json['id'], "modified_at":datetime.now(),"uhid":input_json['uhid'], "bp":input_json['bp'], "bp_sys":input_json['bp_sys'], "bp_dia":input_json['bp_dia'], "heart_rate":input_json['heart_rate'], "temperature":input_json['temperature'],"weight":input_json['weight'],"height":input_json['height'],"respiratory_rate":input_json['respiratory_rate'],"wrist_size":input_json['wrist_size'],"bp_dia2":input_json['bp_dia2'],"bp_sys2":input_json['bp_sys2'],"bp2":input_json['bp2']}

				update_data=database.update_patient_vitals(input_json)

				if update_data == 1:
					return jsonify({"success":1,"message":"updated successfully"})
				else:
					return jsonify({"success":1,"message":"vitals record not found"})

			else:
				return jsonify({"success":0,"message":"vitals not found"})

		else:
			return jsonify({"success":0,"message":"profile not exist for this uhid"})

	except Exception as e:
		print("e1:",e)
		return jsonify({"success":0,"message":"unable to update"})

#create_patient_ measurement
@service_url.route("/create/patient/measurement", methods=['POST'])
# @account
def create_patient_measurement():
	try:
		input_json = request.get_json(force=True)
		if 'uhid' not in input_json:
			return jsonify({'success' : 0, 'message' : 'uhid is missing'})

		uhid = input_json['uhid']
		# uhid =encrypt_raw_data(input_json['uhid']) #uhid encryption
		check_profile=database.check_patient_demographics(uhid,None)

		if check_profile == 1:
			get_profile=database.get_patient_demographics(uhid,None,None,None)

			try:
				if "corrected_bp" not in input_json:
					input_json['corrected_bp']=None
			except:
				input_json['corrected_bp']=None

			if "rawledfile" not in input_json:
				input_json['rawledfile']=''

			if "clibbpsys" not in input_json:
				input_json['clibbpsys']="",
				
			if "clibbpdia" not in input_json:
				input_json['clibbpdia']=""

			if "clib_jsonfile" not in input_json:
				input_json['clib_jsonfile']=""

			if "clib_ppgfile" not in input_json:
				input_json['clib_ppgfile']=""

			if "devicedetails" not in input_json:
				input_json['devicedetails']=""

			if "stitchflag" not in input_json:
				input_json['stitchflag']=""

			if "measurement_questionnaire" not in input_json:
				input_json['measurement_questionnaire']={}

			current_data={"id":str(uuid.uuid4()), "created_at":datetime.now(), "modified_at":datetime.now(), "uhid":input_json['uhid'],"patient_profile_id":get_profile[0]['id'], "bp":input_json['bp'], "bp_sys":input_json['bp_sys'], "bp_dia":input_json['bp_dia'], "bp_measured_date":input_json['bp_measured_date'], "measured_date":input_json['measured_date'], "ppg_file":input_json['ppg_file'], "posture":input_json['posture'], "activity":input_json['activity'], "heart_rate":input_json['heart_rate'], "temperature":input_json['temperature'], "is_active":True,"refbp":input_json['refbp'],"corrected_bp":input_json['corrected_bp'],"gtbp":input_json['gtbp'],"estimated_bp":input_json['estimated_bp'],
			"sqstatus": input_json['sqstatus'],
			"refbpsys": input_json['refbpsys'],
			"refbpdia": input_json['refbpdia'],
			"refbppr": input_json['refbppr'],
			"refgender": input_json['refgender'],
			"refmodel": input_json['refmodel'],
			"refmsamplingf": input_json['refmsamplingf'],
			"estimatedres": input_json['estimatedres'],
			"visitid": input_json['visitid'],
			"calibration":input_json['calibration'],
			"healthstatus":input_json['healthstatus'],
			"clibbpsys":input_json['clibbpsys'],
			"clibbpdia":input_json['clibbpdia'],
			"clib_jsonfile":input_json['clib_jsonfile'],
			"clib_ppgfile":input_json['clib_ppgfile'],
			"devicedetails":input_json['devicedetails'],
			"stitchflag":input_json['stitchflag'],
			"measurement_questionnaire":input_json['measurement_questionnaire'],
			"rawledfile":input_json['rawledfile']
			}

			create_data=database.create_patient_measurement(current_data)

			return jsonify({"success":1,"message":"created successfully"})
		else:
			return jsonify({"success":0,"message":"profile not exist for this uhid"})

	except Exception as e:
		print("e1:",e)
		return jsonify({"success":0,"message":"unable to create"})


#get_patient calibration 
@service_url.route("/get/patient/measurement", methods=['GET'])
# @account
def get_patient_measurement():
	try:
		uhid=request.args.get('uhid',None)
		get_calibration=getpatient_measurement(uhid)
		try:
			if len(get_calibration)!=0:
				for i in get_calibration:
					if 'measurement_questionnaire' not in i:
						i['measurement_questionnaire']={}
		except:
			pass
		get_calibration.sort(key=lambda x: x['created_at'], reverse=True)
		return jsonify({"success":1,"message":get_calibration})
	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to get"})

#get_patient calibration 
def getpatient_measurement(uhid):
	try:
		get_calibration=database.get_patient_measurement(uhid)
		return get_calibration
	except Exception as e:
		print("e5:",e)
		return []

#update_patient_ calibration
@service_url.route("/update/patient/measurement", methods=['POST'])
# @account
def update_patient_measurement():
	try:
		input_json = request.get_json(force=True)
		if 'uhid' not in input_json:
			return jsonify({'success' : 0, 'message' : 'uhid is missing'})

		if 'id' not in input_json:
			return jsonify({'success' : 0, 'message' : 'id is missing'})

		current_time = datetime.now()

		uhid = input_json['uhid']
		# uhid =encrypt_raw_data(input_json['uhid']) #uhid encryption

		check_profile=database.check_patient_demographics(uhid,None)

		if check_profile == 1:
			get_profile=database.get_patient_demographics(uhid,None,None,None)

			check_data=database.check_patient_measurement(uhid)

			if check_data==1:

				try:
					if "corrected_bp" not in input_json:
						input_json['corrected_bp']=None
				except:
					input_json['corrected_bp']=None

				if "rawledfile" not in input_json:
					input_json['rawledfile']=''

				if "clibbpsys" not in input_json:
					input_json['clibbpsys']="",
				
				if "clibbpdia" not in input_json:
					input_json['clibbpdia']=""

				if "clib_jsonfile" not in input_json:
					input_json['clib_jsonfile']=""

				if "clib_ppgfile" not in input_json:
					input_json['clib_ppgfile']=""

				if "devicedetails" not in input_json:
					input_json['devicedetails']=""

				if "measurement_questionnaire" not in input_json:
					input_json['measurement_questionnaire']={}

				input_data={"id":input_json['id'], "modified_at":datetime.now(),"uhid":input_json['uhid'], "bp":input_json['bp'], "bp_sys":input_json['bp_sys'] , "bp_dia":input_json['bp_dia'] ,"bp_measured_date":input_json['bp_measured_date'], "measured_date":input_json['measured_date'], "ppg_file":input_json['ppg_file'],"posture":input_json['posture'], "activity":input_json['activity'], "heart_rate":input_json['heart_rate'], "temperature":input_json['temperature'],"refbp":input_json['refbp'],"corrected_bp":input_json['corrected_bp'],"gtbp":input_json['gtbp'],"estimated_bp":input_json['estimated_bp'],
			"sqstatus": input_json['sqstatus'],
			"refbpsys": input_json['refbpsys'],
			"refbpdia": input_json['refbpdia'],
			"refbppr": input_json['refbppr'],
			"refgender": input_json['refgender'],
			"refmodel": input_json['refmodel'],
			"refmsamplingf": input_json['refmsamplingf'],
			"estimatedres": input_json['estimatedres'],
			"visitid": input_json['visitid'],
			"calibration":input_json['calibration'],
			"healthstatus":input_json['healthstatus'],
			"clibbpsys":input_json['clibbpsys'],
			"clibbpdia":input_json['clibbpdia'],
			"clib_jsonfile":input_json['clib_jsonfile'],
			"clib_ppgfile":input_json['clib_ppgfile'],
			"devicedetails":input_json['devicedetails'],
			"stitchflag":input_json['stitchflag'],
			"measurement_questionnaire":input_json['measurement_questionnaire'],
			"rawledfile":input_json['rawledfile']
			}

				update_data=database.update_patient_measurement(input_data)

				if update_data == 1:
					return jsonify({"success":1,"message":"updated successfully"})
				else:
					return jsonify({"success":1,"message":"measurement record not found"})

			else:
				return jsonify({"success":0,"message":"measurement not found"})

		else:
			return jsonify({"success":0,"message":"profile not exist for this uhid"})

	except Exception as e:
		print("e1:",e)
		return jsonify({"success":0,"message":"unable to update"})



#create_patient_ profile based measurement
@service_url.route("/create/patient/profile/measurement", methods=['POST'])
@account
def create_patient_profile_measurement():
	try:
		input_json = request.get_json(force=True)
		if 'uhid' not in input_json:
			return jsonify({'success' : 0, 'message' : 'uhid is missing'})

		uhid = input_json['uhid']
		# uhid =encrypt_raw_data(input_json['uhid']) #uhid encryption

		check_profile=database.check_patient_demographics(uhid,None)

		if check_profile == 1:
			get_profile=database.get_patient_demographics(uhid,None,None,None)

			current_data={"id":str(uuid.uuid4()), "created_at":datetime.now(), "modified_at":datetime.now(), "uhid":input_json['uhid'],"patient_profile_id":get_profile[0]['id'], "bp":input_json['bp'], "bp_sys":input_json['bp_sys'], "bp_dia":input_json['bp_dia'], "bp_measured_date":input_json['bp_measured_date'], "measured_date":input_json['measured_date'], "ppg_file":input_json['ppg_file'], "posture":input_json['posture'], "activity":input_json['activity'], "heart_rate":input_json['heart_rate'], "temperature":input_json['temperature'], "is_active":True}

			create_data=database.create_patient_profile_measurement(current_data)

			return jsonify({"success":1,"message":"created successfully"})
		else:
			return jsonify({"success":0,"message":"profile not exist for this uhid"})

	except Exception as e:
		print("e1:",e)
		return jsonify({"success":0,"message":"unable to create"})


#get_patient profile based measurement 
@service_url.route("/get/patient/profile/measurement", methods=['GET'])
@account
def get_patient_profile_measurement():
	try:
		uhid=request.args.get('uhid',None)
		get_calibration=getpatient_profile_measurement(uhid)
		return jsonify({"success":1,"message":get_calibration})
	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to get"})

#get_patient profile based  measurement
def getpatient_profile_measurement(uhid):
	try:
		get_calibration=database.get_patient_profile_measurement(uhid)
		return get_calibration
	except Exception as e:
		print("e5:",e)
		return []

#update_patient_ profile based  mesaurement
@service_url.route("/update/patient/profile/measurement", methods=['POST'])
@account
def update_patient_profile_measurement():
	try:
		input_json = request.get_json(force=True)
		if 'uhid' not in input_json:
			return jsonify({'success' : 0, 'message' : 'uhid is missing'})

		if 'id' not in input_json:
			return jsonify({'success' : 0, 'message' : 'id is missing'})

		current_time = datetime.now()

		uhid = input_json['uhid']
		# uhid =encrypt_raw_data(input_json['uhid']) #uhid encryption

		check_profile=database.check_patient_demographics(uhid,None)

		if check_profile == 1:
			get_profile=database.get_patient_demographics(uhid,None,None,None)

			check_data=database.check_patient_profile_measurement(input_json['uhid'])

			if check_data==1:

				input_data={"id":input_json['id'], "modified_at":datetime.now(),"uhid":input_json['uhid'], "bp":input_json['bp'], "bp_sys":input_json['bp_sys'] , "bp_dia":input_json['bp_dia'] ,"bp_measured_date":input_json['bp_measured_date'], "measured_date":input_json['measured_date'], "ppg_file":input_json['ppg_file'],"posture":input_json['posture'], "activity":input_json['activity'], "heart_rate":input_json['heart_rate'], "temperature":input_json['temperature']}

				update_data=database.update_patient_profile_measurement(input_data)

				if update_data == 1:
					return jsonify({"success":1,"message":"updated successfully"})
				else:
					return jsonify({"success":1,"message":"profile measurement record not found"})

			else:
				return jsonify({"success":0,"message":"profile measurement not found"})

		else:
			return jsonify({"success":0,"message":"profile not exist for this uhid"})

	except Exception as e:
		print("e1:",e)
		return jsonify({"success":0,"message":"unable to update"})


# Generate bearer token for the user
def generate_bearer_token(account_id):
	try:
		secrect_key = secrets.token_hex(16)
		security_data = f"{account_id}--{secrect_key}"
		bin_value=binascii.hexlify(security_data.encode())
		token = base64.b64encode(bin_value).decode()
		return token,secrect_key
	except Exception as e:
		return jsonify({'success' : 0, 'message' : 'invalid token'}), 401

#Decode bearer token for the user
def decode_bearer_token(token_encoded):
	try:
		base64_decoded = base64.b64decode(token_encoded)
		decoded_token = binascii.unhexlify(base64_decoded).decode()
		return decoded_token
	except Exception as e:
		response = jsonify({'success' : 0, 'message' : 'invalid token'})
		response.status_code = 401
		return response

#validate bearer token for the user
def validate_bearer_token(request):
	try:
		breare_token = request.headers.get('Authorization').split(' ')[1] if 'Authorization' in request.headers else None
		decode_bearer = decode_bearer_token(breare_token)
		account_id, secrect_key = decode_bearer.split('--')
		if database.check_bearer_token(account_id,secrect_key) == 1:
			token_details = database.get_bearer_token(account_id,secrect_key)
			expires_at = token_details[0]['expires_at']
			if datetime.now() >= expires_at:

				response = jsonify({'success' : 0, 'message' : 'invalid token'})
				response.status_code = 401
				return response

		else:
			response = jsonify({'success' : 0, 'message' : 'invalid token'})
			response.status_code = 401
			return response

	except Exception as e:
		response = jsonify({'success' : 0, 'message' : 'invalid token'})
		response.status_code = 401
		return response


#create bearer token for user name and password
@service_url.route("/bearer/session/create", methods=['POST'])
def breare_session_create():
	try:
		input_json = request.get_json(force=True)
		user_name=(input_json['user_name']).lower()

		phone_number = None
		if int(database.check_operator_demographics(user_name,phone_number)) ==0:
			return jsonify({'success' : 0, 'message' : 'user not exist'})

		password=encode_md5(input_json['password'])
		if int(database.validate_operator_credentials(user_name,password)) ==0:
			return jsonify({'success' : 0, 'message' : 'invalid credentials'}), 401

		get_profile=database.get_operator_demographics(user_name,None)

		header_authorization = request.headers.get('Authorization').split(' ')[1] if 'Authorization' in request.headers else None

		if header_authorization == '7731c839-d1a9-449d-97c8-d4fee7140dfb':
			# Generate bearer token
			bearer_token, secrect_key = generate_bearer_token(get_profile[0]['id'])
		else:
			return jsonify({'success' : 0, 'message' : 'invalid token'}), 401

		token_data = {"id":str(uuid.uuid4()), "created_at":datetime.now(), "modified_at":datetime.now(), "secrect_key": secrect_key, "account_id":get_profile[0]['id'],"expires_at":datetime.now()+timedelta(minutes = 5),"bearer_token":str(bearer_token),"is_active":True}

		create_tokens = database.create_bearer_token(token_data)
		return jsonify({"success": 1, "bearer_token": str(bearer_token)})

	except Exception as e:
		print("e8:",e)
		return jsonify({"success":0,"message":"unable to create session"})

# upload ppg csv file
@service_url.route("/upload/ppg/csv/file", methods=['POST'])
def upload_ppg_csv_file():
	try:
		if request.method == 'POST':

			if 'file' not in request.files:
				return jsonify({"success":0,"message":"no file part"})

			file = request.files['file']

			if file.filename == '':
				return jsonify({"success":1,"message":"no selected file"})

			if file:
				# save_path = 'F:/Office Work/Helyxon/Environment/PPG/' + file.filename
				save_path = '/home/PPG-Python/ppg_files/csv/' + file.filename
				
				file.save(save_path)
				return jsonify({"success":1,"message":"file uploaded successfully","filename":str(file.filename)})

	except Exception as e:
		print("ee:",e)
		return jsonify({"success":0,"message":"unable to upload"})

@service_url.route("/upload/ppg/csv/file/trail", methods=['POST'])
def upload_ppg_csv_file_trail():
	try:

		if 'file' not in request.files:
			return jsonify({"success": 0, "message": "No file part in the request"})

		file = request.files['file']
		
		if file.filename == '':
			return jsonify({"success": 0, "message": "No selected file"})

		if file:
			save_path = f"/home/PPG-Python/ppg_files/csv/{file.filename}"

			file.save(save_path)
			return jsonify({"success": 1, "message": "File uploaded successfully", "filename": file.filename})

	except Exception as e:
		print("ee:",e)
		return jsonify({"success":0,"message":"unable to upload"})
#get uploaded file
@service_url.route('/get/ppg/csv/file', methods=['GET'])
def get_ppg_csv_file():
	try:
		file=request.args.get('file',None)
		# file_path = 'F:/Office Work/Helyxon/Environment/PPG/' + file
		file_path = '/home/PPG-Python/ppg_files/csv/' + file
		return send_file(file_path, as_attachment=True)
	except Exception as e:
		print("ee:", e)
		return jsonify({"success": 0, "message": "unable to get file"})
		

#create_patient_ bp using onnx models
@service_url.route("/estimate/patient/bp", methods=['POST'])
@account
def estimate_patient_bp():
	try:
		if request.method == 'POST':

			if 'file' not in request.files:
				return jsonify({"success":0,"message":"no file part"})

			file = request.files['file']

			if file.filename == '':
				return jsonify({"success":1,"message":"no selected file"})
			
			if file:
				# save_path = 'F:/Office Work/Helyxon/Environment/PPG/' + file.filename
				save_path = '/home/PPG-Python/ppg_files/bp_estimation_files/' + file.filename
				file.save(save_path)

			samplingf= int(request.form.get("samplingf"))
			modelselect= str(request.form.get("modelselect"))
			testid, extension = os.path.splitext(file.filename)

			# Read Reference SBP and DBP, Gender, HR
			try:
				referenceSBP = int(request.form.get("referenceSBP"))
			except:
				referenceSBP = 9998
			try:
				referenceDBP = int(request.form.get("referenceDBP"))
			except:
				referenceDBP = 9998
			try:
				heartRate = int(request.form.get("heartRate"))
				if heartRate == 0:
					heartRate = 9998
			except:
				heartRate = 9998
			try:
				gender = request.form.get("gender")
			except:
				gender = 'N'

			try:
				sqiInfo = int(request.form.get("sqiInfo"))
			except:
				sqiInfo = 0

			result = onnx_model.estimateBP(testid, save_path, samplingf, modelselect, referenceSBP, referenceDBP, heartRate, gender, sqiInfo)
			result = json.loads(result)
			
			return jsonify({"success":1,"message":result})

	except Exception as e:
		print("ee:",e)
		return jsonify({"success":0,"message":"unable to estimate"})


#create_patient_ calibration protocol
@service_url.route("/create/calibration/protocol", methods=['POST'])
@account
def create_calibration_protocol():
	try:

		input_json = request.get_json(force=True)
		if 'user_name' not in input_json:
			return jsonify({'success' : 0, 'message' : 'user_name is missing'})

		for i in input_json['calibration']:
			i.update({"id":str(uuid.uuid4())})

		input_data = {"id":str(uuid.uuid4()),"created_at":datetime.now(), "modified_at":datetime.now()}
		input_data.update(input_json)
		get_profile=database.get_operator_demographics(input_data['user_name'],None)

		if len(get_profile) != 0:
			create_data=database.create_calibrationprotocol(input_data)
			try:
				url = PPG_MAIN_SERVER + "/create/calibration/protocol/trail"
				headers = {
				'Content-Type': 'application/json'
				}
				if 'created_at' in input_data:
					input_data['created_at']=str(input_data['created_at'])
				if 'modified_at' in input_data:
					input_data['modified_at']=str(input_data['modified_at'])
				if 'observation_per_visit' not in input_json:
					input_data['observation_per_visit']=3
				if '_id' in input_data:
					del(input_data['_id'])
				response = requests.request("POST", url, headers=headers, json=input_data)
				print("response:",response)
				# return response
			except Exception as e:
				print("eee:",e)
			return jsonify({"success":1,"message":"created successfully"})
		else:
			return jsonify({"success":0,"message":"profile not exist for this user_name"})

	except Exception as e:
		print("e1:",e)
		return jsonify({"success":0,"message":"unable to create"})


#get_patient_ calibration protocol
@service_url.route("/get/calibration/protocol", methods=['GET'])
@account
def get_calibration_protocol():
	"""
	Get the calibration protocol for a user.

	This function receives the user's name, calibration protocol ID, and calibration type as query parameters.
	It retrieves the calibration protocol based on the provided parameters.

	Returns:
		A JSON response containing the calibration protocol data.

	Raises:
		Exception: If there is an error during the retrieval process.
	"""
	try:
		user_name = request.args.get('user_name', None)
		calibration_id = request.args.get('calibration_id', None)
		calibration_type = request.args.get('calibration_type', 1)
		get_data = database.get_calibrationprotocol(calibration_type, user_name, calibration_id)
		return jsonify({"success": 1, "message": get_data})

	except Exception as e:
		print("e1:", e)
		return jsonify({"success": 0, "message": "unable to get"})

#update_patient_ calibration protocol
@service_url.route("/update/calibration/protocol", methods=['POST'])
@account
def update_calibration_protocol():

	"""
	Update the calibration protocol for a user.

	This function receives a JSON input containing the user's name and the calibration protocol ID.
	It checks if the user profile exists and updates the calibration protocol if it does.
	If the calibration protocol ID does not exist, it returns an error message.

	Returns:
		A JSON response indicating the success or failure of the update.

	Raises:
		Exception: If there is an error during the update process.
	"""
	try:
		input_json = request.get_json(force=True)
		if 'user_name' not in input_json:
			return jsonify({'success' : 0, 'message' : 'user_name is missing'})

		get_profile = database.get_operator_demographics(input_json['user_name'], None)
		if 'observation_per_visit' not in input_json:
			input_json['observation_per_visit']=3
		if len(get_profile) != 0:
			input_json.update({"modified_at": datetime.now()})

			if database.check_calibrationprotocol(input_json['user_name'], input_json['id']) == 1:
				update_data = database.update_calibrationprotocol(input_json)
				try:
					url = PPG_MAIN_SERVER + "/update/calibration/protocol/trail"
					headers = {
					'Content-Type': 'application/json'
					}
					if 'modified_at' in input_json:
						input_json['modified_at']=str(input_json['modified_at'])
		
					if '_id' in input_json:
						del(input_json['_id'])
					response = requests.request("POST", url, headers=headers, json=input_json)
					print("response:",response)
					# return response
				except Exception as e:
					print("eee:",e)
				return jsonify({"success": 1, "message": "updated successfully"})
			else:
				return jsonify({"success": 1, "message": "id does not exist"})
		else:
			return jsonify({"success": 0, "message": "profile does not exist for this user_name"})

	except Exception as e:
		print("e1:", e)
		return jsonify({"success": 0, "message": "unable to update"})


#create admin site
@service_url.route("/create/admin/site", methods=['POST'])
@account
def create_admin_site():

	try:
		input_json = request.get_json(force=True)
		if 'user_name' not in input_json:
			return jsonify({'success' : 0, 'message' : 'user_name is missing'})

		get_profile = database.get_operator_demographics(input_json['user_name'], None)
		if len(get_profile) != 0:

			unique_id = str(uuid.uuid4())
			input_data = {
				"id": unique_id,
				"created_at": datetime.now(),
				"modified_at": datetime.now(),
				"site_name": input_json['site_name'],
				"site_address": input_json['site_address'],
				"is_active": True
			}

			input_json['id'] = unique_id
			create_site = database.create_adminsite(input_data)
			try:
				url = PPG_MAIN_SERVER + "/create/admin/site/trail"
				headers = {
				'Content-Type': 'application/json'
				}
				if 'created_at' in input_data:
					input_data['created_at']=str(input_data['created_at'])
				if 'modified_at' in input_data:
					input_data['modified_at']=str(input_data['modified_at'])
	
				if '_id' in input_data:
					del(input_data['_id'])
				response = requests.request("POST", url, headers=headers, json=input_json)
				print("response:",response)
				# return response
			except Exception as e:
				print("eee:",e)
			return jsonify({"success": 1, "message": "created successfully"})

		else:
			return jsonify({"success": 0, "message": "profile does not exist for this user_name"})

	except Exception as e:
		print("e1:", e)
		return jsonify({"success": 0, "message": "unable to create"})

#get admin site
@service_url.route("/get/admin/site", methods=['GET'])
@account
def get_admin_site():

	try:
		user_name=request.args.get('user_name',None)
		get_profile = database.get_operator_demographics(user_name, None)
		if len(get_profile) != 0:
			get_site = database.get_adminsite()
			return jsonify({"success": 1, "message": get_site})
		else:
			return jsonify({"success": 0, "message": "profile does not exist for this user_name"})

	except Exception as e:
		print("e1:", e)
		return jsonify({"success": 0, "message": "unable to get"})

#update admin site
@service_url.route("/update/admin/site", methods=['POST'])
@account
def update_admin_site():

	try:
		input_json = request.get_json(force=True)
		if 'user_name' not in input_json:
			return jsonify({'success' : 0, 'message' : 'user_name is missing'})

		get_profile = database.get_operator_demographics(input_json['user_name'], None)
		if len(get_profile) != 0:

			input_data=({"id":input_json['id'], "modified_at":datetime.now(),"site_address":input_json['site_address'], "site_name":input_json['site_name']})
			create_site = database.update_adminsite(input_data)
			try:
				url = PPG_MAIN_SERVER + "/update/admin/site/trail"
				headers = {
				'Content-Type': 'application/json'
				}
				if 'modified_at' in input_data:
					input_data['modified_at']=str(input_data['modified_at'])
	
				if '_id' in input_data:
					del(input_data['_id'])
				response = requests.request("POST", url, headers=headers, json=input_json)
				print("response:",response,response.content)
				# return response
			except Exception as e:
				print("eee:",e)
			return jsonify({"success": 1, "message": "updated successfully"})
			
		else:
			return jsonify({"success": 0, "message": "profile does not exist for this user_name"})

	except Exception as e:
		print("e1:", e)
		return jsonify({"success": 0, "message": "unable to update"})


#create_ admin calibration protocol
@service_url.route("/create/admin/protocol", methods=['POST'])
@account
def create_admin_protocol():
	try:

		input_json = request.get_json(force=True)
		if 'user_name' not in input_json:
			return jsonify({'success' : 0, 'message' : 'user_name is missing'})

		for i in input_json['calibration']:
			i.update({"id":str(uuid.uuid4())})
		
		input_data = {"id":str(uuid.uuid4()),"created_at":datetime.now(), "modified_at":datetime.now()}
		input_data.update(input_json)
		if 'observation_per_visit' not in input_data:
			input_data['observation_per_visit']=3
		get_profile=database.get_operator_demographics(input_data['user_name'],None)

		if len(get_profile) != 0:
			create_data=database.create_adminprotocol(input_data)
			try:
				url = PPG_MAIN_SERVER + "/create/admin/protocol/trail"
				headers = {
				'Content-Type': 'application/json'
				}
				if 'created_at' in input_json:
					input_json['created_at']=str(input_json['created_at'])
				if 'modified_at' in input_json:
					input_json['modified_at']=str(input_json['modified_at'])
				if 'observation_per_visit' not in input_json:
					input_json['observation_per_visit']=3
				if '_id' in input_data:
					del(input_json['_id'])
				response = requests.request("POST", url, headers=headers, json=input_json)
				print("response:",response.content)
				# return response
			except Exception as e:
				print("eee:",e)
			return jsonify({"success":1,"message":"created successfully"})
		else:
			return jsonify({"success":0,"message":"profile not exist for this user_name"})

	except Exception as e:
		print("e1:",e)
		return jsonify({"success":0,"message":"unable to create"})


#get_admin_ calibration protocol
@service_url.route("/get/admin/protocol", methods=['GET'])
@account
def get_admin_protocol():

	try:
		user_name = request.args.get('user_name', None)
		calibration_id = request.args.get('calibration_id', None)
		calibration_type = request.args.get('calibration_type', 1) #1-all and 2 - specific
		get_data = database.get_adminprotocol(calibration_type, user_name, calibration_id)
		return jsonify({"success": 1, "message": get_data})

	except Exception as e:
		print("e1:", e)
		return jsonify({"success": 0, "message": "unable to get"})

#update_admin calibration protocol
@service_url.route("/update/admin/protocol", methods=['POST'])
@account
def update_admin_protocol():
 
    try:
        input_json = request.get_json(force=True)
        if 'user_name' not in input_json:
            return jsonify({'success' : 0, 'message' : 'user_name is missing'})
 
        get_profile = database.get_operator_demographics(input_json['user_name'], None)
        if len(get_profile) != 0:
            input_json.update({"modified_at": datetime.now()})
 
            if 'observation_per_visit' not in input_json:
                input_json['observation_per_visit']=3
 
            if database.check_adminprotocol(input_json['user_name'], input_json['id']) == 1:
                update_data = database.update_adminprotocol(input_json)
                return jsonify({"success": 1, "message": "updated successfully"})
            else:
                return jsonify({"success": 1, "message": "id does not exist"})
        else:
            return jsonify({"success": 0, "message": "profile does not exist for this user_name"})
 
    except Exception as e:
        print("e1:", e)
        return jsonify({"success": 0, "message": "unable to update"})


#get_operator_profile list
@service_url.route("/get/operator/list", methods=['GET'])
@account
def get_operator_list():
	try:
		get_calibration=database.get_operator_list()

		return jsonify({"success":1,"message":get_calibration})
	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to get"})


# get_patient measurement data report 
# @service_url.route("/get/patient/measurement/report", methods=['GET'])
# @account
# def get_patient_measurement_report():
# 	try:
# 		uhid=request.args.get('uhid',None)
# 		from_date=request.args.get('from_date',None)
# 		to_date=request.args.get('to_date',None)

# 		if uhid != None and uhid != "null":
# 			patient_data=patient_measurement_data(from_date,to_date,uhid)
# 			final_data=[patient_data]
# 		else:
# 			patient_list=database.get_measurement_patient_list(from_date,to_date)
# 			final_data=[]
# 			for i in patient_list:
# 				patient_data=patient_measurement_data(from_date,to_date,i)
# 				final_data.append(patient_data)

# 		# final_data.sort(key=lambda x: x['measurement'][0]['created_at'], reverse=True)
# 		final_data=sorted(final_data,key=lambda i:(i['measurement'][0]['created_at']),reverse=True)
# 		return jsonify({"success":1,"message":final_data})
# 	except Exception as e:
# 		print("e5:",e)
# 		return jsonify({"success":0,"message":"unable to get"})

def patient_measurement_data(from_date,to_date,uhid):
	try:
		patient_data={}
		get_measurement=database.get_patient_measurement_report(from_date,to_date,uhid)
		patient_data['measurement']=get_measurement
		try:
			for i in get_measurement:
				if "measurement_questionnaire" not in i:
					i["measurement_questionnaire"]={}
		except:
			pass
		try:
			vital_data = database.get_patient_vitals(uhid)[0]
			patient_data['vital_details'] = vital_data
		except Exception as e:
			patient_data['vital_details']={}

		try:
			health_record=get_patienthealth_record(uhid)
			patient_data['health_record']=health_record[0]
		except Exception as e:
			print("e:",e)
			patient_data['health_record']={}

		try:
			# uhid =encrypt_raw_data(uhid) #uhid encryption
			get_profile=database.get_patient_demographics(uhid,None,None,None)
			site_details=database.get_patient_sitedetails(get_profile[0]['id'])
			patient_data['operator_name']=site_details[0]['operator_name']
			patient_data['device_details']=site_details[0]['device_details']
			patient_data['device_address']=site_details[0]['device_address']
			patient_data['device_brand']=site_details[0]['device_brand']
			patient_data['site_name']=site_details[0]['site_name']
		except Exception as e:
			print("e:",e)
			patient_data['operator_name'] = ""
			patient_data['device_details'] = ""
			patient_data['device_address'] = ""
			patient_data['device_brand'] = ""
			patient_data['site_name'] = ""

		try:
			patient_data['age'] = get_profile[0]['age']
			patient_data['gender'] = get_profile[0]['gender']
			patient_data['etnicity'] = get_profile[0]['etnicity']
			get_health = database.get_patient_healthrecord(get_profile[0]['id'])
			patient_data['chief_complaint'] = get_health[0]['chief_complaint']
			patient_data['notes'] = get_health[0]['notes']
			patient_data['site_name'] = site_details[0]['site_name']
			patient_data['device_address'] = site_details[0]['device_address']
			patient_data['operator_name'] = site_details[0]['operator_name']
			patient_data['date_of_registration'] = get_profile[0]['created_at'].date()
			patient_data['registration_complete_time'] = get_profile[0]['created_at']
			get_measuremnet = database.get_patient_measurement(get_profile[0]['id'])
			patient_data['measurement_complete_time'] = get_measuremnet[0]['created_at']
		except:
			patient_data['age'] = ""
			patient_data['gender'] = ""
			patient_data['etnicity'] = ""
			patient_data['chief_complaint'] = ""
			patient_data['notes'] = ""
			patient_data['site_name'] =""
			patient_data['device_address'] =""
			patient_data['operator_name'] =""
			patient_data['date_of_registration'] =""
			patient_data['registration_complete_time'] =""
			patient_data['measurement_complete_time'] = ""
		return patient_data
	except Exception as e:
		print("e5:",e)
		return {}

#upload ota files
@service_url.route("/upload/otafiles", methods=['POST'])
@account
def upload_otafiles():
	try:
		if request.method == 'POST':

			if 'file' not in request.files:
				return jsonify({"success": 0, "message": "No file part"})

			files = request.files.getlist('file')
			if not files or all(f.filename == '' for f in files):
				return jsonify({"success": 0, "message": "No selected files"})

			folder_name = request.form.get('folder_name')
			version = request.form.get('version')

			if not folder_name:
				return jsonify({"success": 0, "message": "folder_name is missing"})
			if not version:
				return jsonify({"success": 0, "message": "version is missing"})

			directory_name = f'/var/www/html/ppg/otafiles/{folder_name}/'
			if not os.path.isdir(directory_name):
				os.makedirs(directory_name, exist_ok=True)

			saved_files = []
			for file in files:
				save_path = os.path.join(directory_name, file.filename)
				file.save(save_path)
				saved_files.append({"filename": file.filename, "path": save_path})

			input_data = {
				"id": str(uuid.uuid4()),
				"created_at": str(datetime.now()),
				"modified_at": str(datetime.now()),
				"folder_name": folder_name,
				"version": version,
				"is_active": True,
			}

			if not database.check_otafile(folder_name):
				database.create_otafile(input_data)

			try:
				url = PPG_MAIN_SERVER + "/upload/otafiles/trail"
				if '_id' in input_data:
					del input_data['_id']
				input_data['created_at'] = str(input_data['created_at'])
				input_data['modified_at'] = str(input_data['modified_at'])

				file_data = [
					('file', (file['filename'], open(file['path'], 'rb'), 'application/octet-stream'))
					for file in saved_files
				]

				response = requests.post(url, data=input_data, files=file_data)
				print("response:", response.content)
			except Exception as e:
				print("eee:",e)
			return jsonify({"success":1,"message":"uploaded sucessfully"})

	except Exception as e:
		print("ee:",e)
		return jsonify({"success":0,"message":"unable to upload"})



#upload ota files
@service_url.route("/upload/otafiles/new", methods=['POST'])
@account
def upload_otafiles_new():
	try:
		if request.method == 'POST':

			# if 'file' not in request.files:
			# 	return jsonify({"success":0,"message":"no file part"})

			file = request.files['file']

			file = request.files.getlist('file')

			if file:	
				if file.filename == '':
					return jsonify({"success":0,"message":"no selected file"})

				if not request.form.get('folder_name'):
					return jsonify({"success":0,"message":"folder_name is missing"})

				if not request.form.get('version'):
					return jsonify({"success":0,"message":"version is missing"})

				version = request.form.get('version')
				folder_name = request.form.get('folder_name')
				for i in request.files.getlist('file'):

					# directory_name = 'F:/Office Work/Helyxon/Environment/PPG/' + folder_name + '/'
					directory_name = '/var/www/html/ppg/otafiles/' + folder_name + '/'

					if not os.path.isdir(directory_name):
						create_dir = os.makedirs(directory_name, exist_ok=True)

					save_path = directory_name + i.filename
					file.save(save_path)

				if database.check_otafile(folder_name) == False :
					input_data = {"id":str(uuid.uuid4()),"created_at":datetime.now(), "modified_at":datetime.now(), "folder_name":folder_name, "version":version, "is_active":True}
					create_data = database.create_otafile(input_data)
			else:
				return jsonify({"success":0,"message":"no selected file"})
			try:
				url = PPG_MAIN_SERVER + "/upload/otafiles/new/trail"
				headers = {
				'Content-Type': 'application/json'
				}
				if 'created_at' in input_data:
					input_data['created_at']=str(input_data['created_at'])
				if 'modified_at' in input_data:
					input_data['modified_at']=str(input_data['modified_at'])
	
				if '_id' in input_data:
					del(input_data['_id'])

				response = requests.request("POST", url, headers=headers, data=input_data)
				print("response:",response)
				# return response
			except Exception as e:
				print("eee:",e)
			return jsonify({"success":1,"message":"uploaded sucessfully"})

	except Exception as e:
		print("ee:",e)
		return jsonify({"success":0,"message":"unable to upload"})



#get ota files
@service_url.route("/get/otafiles", methods=['GET'])
@account
def get_otafiles():
	try:
		file_type=int(request.args.get('file_type',1))
		folder_name=request.args.get('folder_name',None)

		if file_type == 0: #get specified filed

			try:
				# file_path = 'F:/Office Work/Helyxon/Environment/PPG/' + folder_name 
				file_path = '/var/www/html/ppg/otafiles/' + folder_name
				cloud_url = '/ppg/otafiles/' + folder_name
				file_path_list = os.listdir(file_path)
			except:
				return jsonify({"success": 0, "message": "enter valid folder_name "})

			get_data = database.get_otafile(folder_name)
			final_data=[]
			for i in file_path_list:
				final_data.append(cloud_url+'/'+i)

		else: #get latest files only
			get_data = database.get_latest_otafile()
			del(get_data[0]['_id'])
			# file_path = 'F:/Office Work/Helyxon/Environment/PPG/' + folder_name 
			file_path = '/var/www/html/ppg/otafiles/' + get_data[0]['folder_name']
			cloud_url = '/ppg/otafiles/' + get_data[0]['folder_name']
			file_path_list = os.listdir(file_path)
			
			final_data=[]
			for i in file_path_list:
				final_data.append(cloud_url+'/'+i)
		
		final_json={"ota_data":get_data,"file_path":final_data}
		return jsonify({"success": 1, "message": final_json})

	except Exception as e:
		print("ee:", e)
		return jsonify({"success": 0, "message": "unable to get file"})

#get ota files list
@service_url.route("/get/otafiles/list", methods=['GET'])
@account
def get_otafiles_list():
	try:
		get_data = database.get_latest_otafile_list()
		final_data=[]
		for i in get_data:
			del(i['_id'])

		return jsonify({"success": 1, "message": get_data})

	except Exception as e:
		print("ee:", e)
		return jsonify({"success": 0, "message": "unable to get file"})

#create_patient_  bp using c-library models
@service_url.route("/estimate/patient/clib/bp", methods=['POST'])
@account
def estimate_patient_clib_bp():
	try:
		if request.method == 'POST':

			if 'file' not in request.files:
				return jsonify({"success":0,"message":"no file part"})

			file = request.files['file']

			if file.filename == '':
				return jsonify({"success":1,"message":"no selected file"})
			
			if file:
				# save_path = 'F:/Office Work/Helyxon/Environment/PPG/C-Library/exec/pre_denoise/' + file.filename
				save_path = '/var/www/html/ppg/exec/pre_denoise/' + file.filename
				print("save_path:",save_path)
				file.save(save_path)

			record_name= request.form.get("record_name",None)
			sampling_frequency= request.form.get("sampling_frequency",None)
			analysis_flag= request.form.get("analysis_flag",None)
			data_duration= request.form.get("data_duration",None)
			de_noise_flag= int(request.form.get("de_noise_flag",0))
			stitch_flag= int(request.form.get("stitch_flag",0))

			# Set the LD_LIBRARY_PATH environment variable
			set_library = os.environ['LD_LIBRARY_PATH'] = '/home/PPG-Python/ppg/C-Library/exec/'

			command = ['/home/PPG-Python/ppg/C-Library/exec/libPPG_V1.2.2S', '/var/www/html/ppg/exec/pre_denoise/'+str(file.filename), '/var/www/html/ppg/exec/post_denoise/', str(record_name), str(sampling_frequency), str(analysis_flag), str(data_duration), str(de_noise_flag), str(stitch_flag)]

			print("command:",command)

			result = subprocess.run(command, capture_output=True, text=True)
			print('getresult',result)

			denoise_json_file = '/var/www/html/ppg/exec/post_denoise/'+record_name+'_RecSession.json'
			denoise_json= '/ppg/exec/post_denoise/'+record_name+'_RecSession.json'
			denoise_csv= '/ppg/exec/post_denoise/'+record_name+'_DenoiseData.csv'
			
			with open(denoise_json_file, 'r') as denoise_file:
				data = json.load(denoise_file)
				
			denoise_data = {"csv_file":denoise_csv,"json_file":denoise_json,"json_data":data}

			return jsonify({"success":1,"message":denoise_data})
	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
                        f"line no: {exc_tb.tb_lineno} | {ex}")
		return AppUtils.responseWithoutData(0, 400, "Bad Request")


#create_patient_  bp using c-library models
@service_url.route("/estimate/patient/clib/bp/dump/", methods=['POST'])
@account
def estimate_patient_clib_bp_dump():
	try:
		if request.method == 'POST':

			get_dump_data = database.get_patient_measurement_dump()
			success_count=0
			fail_count=0

			for i in get_dump_data:

				source_path = '/home/PPG-Python/ppg_files/csv/'+str(i['ppg_file']) #+'.csv'

				try:
					df = pd.read_csv(source_path)
					record_count = len(df)
					# print("record_count:",record_count)
					if int(record_count) == 1999:
						pass
					else:
						continue
				except:
					continue

				destination_folder = '/var/www/html/ppg/exec/pre_denoise/'
				destination_path = os.path.join(destination_folder, os.path.basename(source_path) + '.csv')
				# Check if the source file exists before attempting to copy
				if os.path.exists(source_path):
					# Copy the file
					shutil.copy(source_path, destination_path)
					print("Source file copied")
				else:
					print("Source file does not exist")

				get_demo_data = database.get_patient_demographics_dump(i['patient_profile_id'])
				record_name= get_demo_data[0]['first_name'].replace(" ", "")+"_"+"CLib_DenoiseData"+"_"+str(int(time.time()))#+".csv"

				sampling_frequency='100.0'
				analysis_flag= '2.0'
				data_duration= '20.0'
				de_noise_flag= '0.0'
				stitch_flag= '0.0'

				# Set the LD_LIBRARY_PATH environment variable
				set_library = os.environ['LD_LIBRARY_PATH'] = '/home/PPG-Python/ppg/C-Library/exec/'	
				command = ['/home/PPG-Python/ppg/C-Library/exec/libPPG_V1.2.2S', '/var/www/html/ppg/exec/pre_denoise/'+str(i['ppg_file'])+'.csv', '/var/www/html/ppg/exec/post_denoise/', str(record_name), sampling_frequency, analysis_flag, data_duration, de_noise_flag,stitch_flag]

				result = subprocess.run(command, capture_output=True, text=True)

				denoise_json_file = '/var/www/html/ppg/exec/post_denoise/'+record_name+'_RecSession.json'
				denoise_json= '/ppg/exec/post_denoise/'+record_name+'_RecSession.json'
				denoise_csv= '/ppg/exec/post_denoise/'+record_name+'_DenoiseData.csv'
				try:

					with open(denoise_json_file, 'r') as denoise_file:
						data = json.load(denoise_file)

					denoise_data = {"csv_file":denoise_csv,"json_file":denoise_json,"json_data":data}
					input_data = {"id":i['id'],"patient_profile_id":i['patient_profile_id'],"clibbpsys":data['eSBP'], "clibbpdia":data['eDBP'],"clib_jsonfile":str(denoise_json),"clib_ppgfile":str(denoise_csv)}

					update_dump = database.update_patient_measurement_dump(input_data)
					success_count+=1

				except Exception as e:
					fail_count+=1
					print("ee exp:",e)

			return jsonify({"success":1,"message":"successfully loaded"})

	except Exception as e:
		print("ee:",e)
		return jsonify({"success":0,"message":"unable to estimate"})


#get ota files list
@service_url.route("/generate/secrect/tokens", methods=['GET'])
@account
def generate_secrect_keys():
	try:
		get_data = generate_secrect_keys()
		return jsonify({"success": 1, "message": get_data})
	except Exception as e:
		print("ee:", e)
		return jsonify({"success": 0, "message": "unable to generate"})

# generate secrect public and private keys to encrypt raw data
def generate_secrect_keys():
	try:
		generate_sender_secrect = fidelius.getEcdhKeyMaterial() #generate security keys
		generate_receiver_secrect = fidelius.getEcdhKeyMaterial() #generate security keys
		current_time = datetime.now()
		security_keys = {"id":str(uuid.uuid4()), "created_at":current_time, "modified_at":current_time,"sender_secrect":generate_sender_secrect,"receiver_secrect":generate_receiver_secrect}

		return security_keys
	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to generate"})

# encrtpt raw data
def encrypt_raw_data(raw_data):
	try:
		#encrypt logic
		stringToEncrypt=raw_data
		receiver_public_key="BB4AQmFr6a7ByZxoEd9sU6indPRKL+MKwZVTIGkzvssBYNJqVQhcV45ODCZqQQh+tS9FsRwYZSL6ySkiAp2+MGc="
		receiver_nonce_key="7xniOoj1C21ZIqCDORtaER7RJ0/80VOhuJqbKj5aEyI="
		sender_private_key="Cl2LcQlT70Q32PJ7qT9ZkzEOCEkazoh9vMTXbQF5glI="
		sender_nonce="1JVXM/017O9vtwe/Y5mQjWqwM3TcCFE34O1rNZG2Exs="

		if isinstance(stringToEncrypt, dict):
			for key,stringToEncrypt  in raw_data.items():

				if key == 'created_at' or key == 'modified_at' or key == 'id' or key == 'is_active' or type(stringToEncrypt) == bool:
					continue

				if isinstance(stringToEncrypt, dict) or isinstance(stringToEncrypt, list) :
					stringToEncrypt=str(stringToEncrypt)

				Encryptdata = fidelius.Encryptor(stringToEncrypt,receiver_public_key,receiver_nonce_key,sender_private_key,sender_nonce)
				raw_data[key] = Encryptdata['encryptedData']

		elif isinstance(stringToEncrypt, str):
			Encryptdata = fidelius.Encryptor(stringToEncrypt,receiver_public_key,receiver_nonce_key,sender_private_key,sender_nonce)
			raw_data = Encryptdata['encryptedData']
		else:
			return "not valid type"

		return raw_data

	except Exception as e:
		print("encrypt err:",e)
		return jsonify({"success":0,"message":"unable to encrypt"})


#create sample api
@service_url.route("/create/sample/", methods=['POSt'])
# @account
def create_sample():
	try:
		input_json = request.get_json(force=True)
		input_json = encrypt_raw_data(input_json)
		create_data = database.create_encrtpted_data(input_json)

		return jsonify({"success":1,"message":"successfully created"})

	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to create"})


# decrtpt raw data
def decrypt_raw_data(raw_data):
	try:
		#decrypt logic
		sender_public_key = "BECPsc9S1Lf9b4hi1OuBCq104Evjex2kB+S6y3ioWmwgBnYrKuZrRzCAdpu1ztrtrIYBEp2x1M6K1ARDVBP2zN4="
		receiver_nonce_key="7xniOoj1C21ZIqCDORtaER7RJ0/80VOhuJqbKj5aEyI="
		receiver_private_key="CijkFOSsK1Tv6rAZspWJ++CEwB5SUsA7sqhKNe2vsVQ="
		sender_nonce="1JVXM/017O9vtwe/Y5mQjWqwM3TcCFE34O1rNZG2Exs="

		if isinstance(raw_data, dict): 

			for key, encryptedData in raw_data.items():
				if key == 'created_at' or key == 'modified_at' or key == 'id' or key == 'is_active' or type(encryptedData) == bool:
					continue
				Decryptdata = fidelius.Decryptor(encryptedData, receiver_nonce_key, sender_nonce, receiver_private_key, sender_public_key)
				raw_data[key] = Decryptdata['decryptedData']

		elif isinstance(raw_data, str):
			Decryptdata = fidelius.Decryptor(encryptedData, receiver_nonce_key, sender_nonce, receiver_private_key, sender_public_key)
			raw_data = Decryptdata['decryptedData']

		else:
			return "not valid type"

		return raw_data

	except Exception as e:
		print("decrypt err:",e)
		return jsonify({"success":0,"message":"unable to decrypt"})

#get sample api
@service_url.route("/get/sample/", methods=['GET'])
# @account
def get_sample():
	try:
		name=request.args.get('name',None)
		name = encrypt_raw_data(name)
		get_encrypted=database.get_encrtpted_data(name)
		decrypted_data=decrypt_raw_data(get_encrypted[0])
		return jsonify({"success":1,"message":get_encrypted})

	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to get"})

@service_url.route("/get/patient/measurement/report", methods=['GET'])
@account
def get_patient_measurement_reportdata():
	try:
		uhid=request.args.get('uhid',None)
		from_date=request.args.get('from_date',None)
		to_date=request.args.get('to_date',None)
		if uhid:
			url = PPG_MAIN_SERVER + "/get/patient/measurement/report/trail?from_date={0}&to_date={1}&uhid={2}".format(from_date,to_date,uhid)
		else:
			url = PPG_MAIN_SERVER + "/get/patient/measurement/report/trail?from_date={0}&to_date={1}".format(from_date,to_date)
		response = requests.request("GET", url )
		content = ((response.content).decode("utf-8"))
		return json.loads(content)
	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to get"})
	
#get_patient measurement data report
@service_url.route("/get/patient/last/measurement", methods=['GET'])
# @account
def get_patient_last_measurement_report():
    try:
        uhid=request.args.get('uhid',None)
        patient_data=database.get_patient_last_measurement(uhid)
        return jsonify({"success":1,"message":patient_data})
    except Exception as e:
        print("e5:",e)
        return jsonify({"success":0,"message":"unable to get"})


@service_url.route("/execution/summary/report", methods=['GET'])
# @account
def execution_summary_report():
	try:
		from_date=request.args.get('from_date',None)
		to_date=request.args.get('to_date',None)
		compute_server = 1
		url = PPG_MAIN_SERVER + "/execution/summary/report?from_date={0}&to_date={1}&compute_server={2}".format(from_date,to_date,compute_server)
		response = requests.request("GET", url )
		content = ((response.content).decode("utf-8"))
		return json.loads(content)
	except Exception as e:
		print("e5:",e)
		return jsonify({"success":0,"message":"unable to get"})
	

##################################################################
##create_patient_profile phase 2
##################################################################
@service_url.route("/v2/create/patient/profile", methods=['POST'])
# @account
def create_patient_profilev2():
	try:
		input_json = request.get_json(force=True)
		demographics_data = input_json.copy()
		ref_bp = demographics_data.pop("ref_bp", None)
		ref_hr = demographics_data.pop("ref_hr", None)
		demographics_data["created_at"] = datetime.utcnow()
		demographics_data["modified_at"] = None
		demographics_data["uhid"] = database.generate_uhid_safe()
		hashedPwd = AuthHandler().getPasswordHash(password=input_json['password'])
		demographics_data['password']=hashedPwd
		if demographics_data:
			patient_id=database.create_patient_demographics(demographics_data,return_id=True)
			patient_log=database.create_patient_demographics_log(demographics_data)
			patient_health_input={
				"created_at":demographics_data['created_at'],
				"modified_at":None,
				"patient_profile_id":str(patient_id),
				"uhid":demographics_data['uhid'],
				"health_status":"",
				"medical_history":"",
				"consent_obtained":"",
				"calibration_needed":"",
				"calibration_protocol":"",
				"observation_per_visit":0,
				"chief_complaint":"",
				"is_active":True,
				"notes":""
			}
			create_health_data=database.create_patient_healthrecord(patient_health_input)
			if ref_bp or ref_hr:
				bp_sys, bp_dia = ref_bp.split('/')
				vitals_data = {
                "patient_profile_id": str(patient_id),  # Store as string or ObjectId based on your schema
                "bp": ref_bp,
				"bp_sys":bp_sys,
				"bp_dia":bp_dia,
                "heart_rate": ref_hr,
				"temperature":"",
				"weight":"",
				"height":"",
				"is_active":True,
				"respiratory_rate":"",
				"wrist_size":"",
				"bp_dia2":"",
				"bp_sys2":"",
				"bp2":"",
				"created_at":demographics_data['created_at'],
				"modified_at":None,
				"uhid":demographics_data['uhid'],
                }
				create_data=database.create_patientvitals(vitals_data)	
				return AppUtils.responseWithoutData(1,201,"Demographics created successfully")
			else:
				return AppUtils.responseWithoutData(0,400, "Missing params BP or heart rate")
		else:
			return AppUtils.responseWithoutData(0, 400, "Please check the input data")
	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
                        f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0,400, responseMsg)
	
##################################################################
##List patient_profile phase 2
##################################################################
@service_url.route("/v2/patient/profile/list", methods=['GET'])
@AuthHandler.auth_required
def list_patient_profilev2():
	try:
		# Get query parameters with default values
		page = int(request.args.get("page", 1))
		limit = int(request.args.get("limit", 10))
		skip = (page - 1) * limit

		# Fetch paginated data
		get_patient_demographics, total_count = database.get_patient_demographicsv2(skip, limit)

		response = {
			"current_page": page,
			"per_page": limit,
			"total_records": total_count,
			"total_pages": (total_count + limit - 1) // limit,
			"data": get_patient_demographics
		}

		return AppUtils.responseWithData(1, 200, 'Patient details found', response)

	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
                        f"line no: {exc_tb.tb_lineno} | {ex}")
		return AppUtils.responseWithoutData(0, 400, "Bad Request")

##################################################################
##List patient_profile phase 2
##################################################################
@service_url.route("/v2/patient/profile/get", methods=['POST'])
@AuthHandler.auth_required
def get_patient_profilev2():
	try:
		input_json = request.get_json(force=True)
		demographics_data = input_json.copy()
		if demographics_data and demographics_data['uhid']:
			get_patient_demographics=database.get_patient_demographics2(demographics_data['uhid'],None)
			if get_patient_demographics!=[]:
				get_patient_health_record=database.get_patient_healthrecord(demographics_data['uhid'])
				get_patient_vital_data=database.get_patient_vitals(demographics_data['uhid'])
				userResponsedata = get_patient_demographics[0]
				device_id_str = str(get_patient_demographics[0]['device_info_id'])
				device_info=database.get_device_data(ObjectId(device_id_str))
				userResponsedata['device_info']=device_info
				patient_details={
					'patient_demographics_data':userResponsedata,
					'patient_vitals_data':get_patient_vital_data[0],
					'patient_health_record':get_patient_health_record[0]
				}
				return AppUtils.responseWithData(1,200,"Patient details found",patient_details)
			else:
				return AppUtils.responseWithoutData(0,404,"Patient details not found")

		else:
			return AppUtils.responseWithoutData(0,400,"Please check the input")

	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
                        f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0,400, responseMsg)

##################################################################
##update patient profile phase 2
##################################################################
@service_url.route("/v2/update/patient/profile", methods=['PATCH'])
def update_patient_profilev2():
	try:
		input_json = request.get_json(force=True)
		demographics_data = input_json.copy()
		ref_bp = demographics_data.pop("ref_bp", None)
		ref_hr = demographics_data.pop("ref_hr", None)
		demographics_data['id']=ObjectId(demographics_data['id'])
		demographics_data["modified_at"] = datetime.utcnow()
		if demographics_data:
			patient_update_data=database.update_patient_demographicsv2(demographics_data)
			patient_log=database.update_patient_demographics_logv2(demographics_data)
			patient_health_input={
				"modified_at":demographics_data['modified_at'],
				"health_status":"",
				"medical_history":"",
				"consent_obtained":"",
				"calibration_needed":"",
				"calibration_protocol":"",
				"observation_per_visit":0,
				"chief_complaint":"",
				"is_active":demographics_data['is_active'] if demographics_data.get('is_active') else True,
				"notes":"",
				"uhid":demographics_data["uhid"]
			}
			update_health_data=database.update_patient_healthrecordv2(patient_health_input)
			if ref_bp or ref_hr:
				bp_sys, bp_dia = ref_bp.split('/')
				vitals_data = {
                "bp": ref_bp,
				"bp_sys":bp_sys,
				"bp_dia":bp_dia,
                "heart_rate": ref_hr,
				"temperature":"",
				"weight":"",
				"height":"",
				"is_active":demographics_data['is_active'] if demographics_data.get('is_active') else True,
				"respiratory_rate":"",
				"wrist_size":"",
				"bp_dia2":"",
				"bp_sys2":"",
				"bp2":"",
				"modified_at":demographics_data['modified_at'],
				"uhid":demographics_data['uhid'],
                }
				update_data=database.update_patient_vitalsv2(vitals_data,None)	
				return AppUtils.responseWithoutData(1,200,"Demographics updated successfully")
			else:
				return AppUtils.responseWithoutData(0,400, "Missing params BP or heart rate")
		else:
			return AppUtils.responseWithoutData(0, 400, "Please check the input data")
	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
						f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0,400, responseMsg)

##################################################################
##Inactive patient profile phase 2
##################################################################
@service_url.route("/v2/patient/profile/deactivate", methods=['PATCH'])
@AuthHandler.auth_required
def deactivate_patient_profilev2():
	try:
		input_json = request.get_json(force=True)
		input_json['modified_at']=datetime.now()
		if input_json.get('uhid') is not None:
			inactive_patient_profile=database.inactive_patient_profile(input_json)
			inactive_patient_vitals=database.inactive_patient_vitals(input_json)
			inactive_patient_healthrecord=database.inactive_patient_health_record(input_json)
			return AppUtils.responseWithoutData(1, 200, "Patient records deactivated successfully")
		else:
			return AppUtils.responseWithoutData(0, 400, "Missing param 'uhid'")
	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
						f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0,400, responseMsg)

#################################################################
## Patient Login version2
#################################################################

@service_url.route("/v2/patient/profile/login", methods=['POST'])
# @account
def patient_loginv2():
	try:
		input_json = request.get_json(force=True)
		check_user=database.check_user_credentials(input_json['user_name'])
		if check_user==0:
			return AppUtils.responseWithoutData(0,404, "User not found")
		elif check_user is not None and check_user[0]['is_active'] == False:
			return AppUtils.responseWithoutData(0,403, "User is inactive.Please contact administrator")
		elif check_user[0]['user_name'].strip() == "" or check_user[0]['password'].strip() == "":
			return AppUtils.responseWithoutData(0,401, "Invalid credentials")
		verified = AuthHandler().verifyPassword(
            input_json['password'], check_user[0]['password'])
		if not verified:
			return AppUtils.responseWithoutData(0,401, "Invalid credentials")
		token = AuthHandler().encodeToken(check_user[0]['user_name'])
		userResponsedata = check_user[0]
		device_id_str = str(check_user[0]['device_info_id'])
		device_info=database.get_device_data(ObjectId(device_id_str))
		userResponsedata['device_info']=device_info
		uhid=check_user[0]['uhid']
		patient_vitals_data=database.get_patient_vitals(uhid)
		patient_health_record=database.get_patient_healthrecord(uhid)
		patient_details={
			'patient_demographics_data':userResponsedata,
			'patient_vitals_data':patient_vitals_data[0],
			'patient_health_record':patient_health_record[0],
			'token':token
		}
		return AppUtils.responseWithData(1,200, "Logged In successfully",patient_details )		
	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
                        f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0,400, responseMsg)


#################################################################
## Creating PPG Device Info
#################################################################
@service_url.route("/v2/device/create", methods=['POST'])
@AuthHandler.auth_required
def create_device():
	try:
		input_json = request.get_json(force=True)
		input_json["created_at"] = datetime.utcnow()
		input_json['modified_at'] = datetime.utcnow()
		create_data = database.create_device_data(input_json)
		return AppUtils.responseWithoutData(1, 201, "Device info created successfully")

	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
						f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0, 400, responseMsg)


#################################################################
## Get all PPG Device Info
#################################################################
@service_url.route("/v2/device/get", methods=['GET'])
@AuthHandler.auth_required
def get_all_device():
	try:
		get_all_device_data = database.get_device_data()
		return AppUtils.responseWithData(1, 200, "Device info found",get_all_device_data)
	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
						f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0, 400, responseMsg)
	
#################################################################
## Update PPG Device Info
#################################################################
@service_url.route("/v2/device/update", methods=['PATCH'])
@AuthHandler.auth_required
def update_device():
	try:
		input_json = request.get_json(force=True)
		updatedData=database.update_device_data(input_json)
		if updatedData.get('status')==1:
			return AppUtils.responseWithoutData(1, 200, "Device data updated successfully")
		else:
			return AppUtils.responseWithoutData(0, 500, "Failed to update the data")
	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
						f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0, 400, responseMsg)
	
##################################################################
## Execution summmary report
##################################################################

def execution_summary_report_calculation(get_patient):
		try:

			get_patient = [get_patient]

			total_male=0
			total_female=0
			total_patient=0

			total_measured_episodes_count = 0#len(total_measured_episodes)0

			completed_measurement_count = 0
			incompleted_measurement_count = 0

			prehypertension = 0
			prehypertension_male = 0
			prehypertension_female = 0
		
			hypertension_stage1 = 0	
			hypertension_stage1_male = 0
			hypertension_stage1_female = 0
		
			hypertension_stage2 = 0
			hypertension_stage2_male = 0
			hypertension_stage2_female = 0

			normal = 0
			normal_male = 0
			normal_female = 0

			Group_35_45=0
			Group_46_55=0
			Group_56_65=0
			Group_66_75=0
			Group_above_75=0
			Group_below_35=0

			lost_to_followup=0

			total_uhid_list = []
			completed_uhid_list = []
			incompleted_uhid_list = []
			lost_uhid_list = []

			for uhid in get_patient:

				total_uhid_list.append(uhid)

				measurement_data = database.get_measurement_date_list(uhid)
				subject_measurement_status = measurement_data[0]
				total_measured_episodes_count += measurement_data[1]
				patient_data = database.get_patient_demographics2(uhid,None)

				try:
					#Condition 1 : Subjects Registered but no data available, Registration is completed one month from the current date.
				
					if subject_measurement_status == False:
						current_date = datetime.now()
						one_month_ago = current_date - relativedelta(months=1)
						patient_account_created = patient_data[0]['created_at']
						date_counts = measurement_data[1]
						ppg_recods = measurement_data[2]
						date_grouping = measurement_data[3]
						# print("uhid : ",uhid,", date_counts:",date_counts)
						# print("uhid : ",uhid,", ppg_recods:",ppg_recods)
						# print("uhid : ",uhid,", date_grouping:",date_grouping)
					
						if date_counts == 0:
							if one_month_ago > patient_account_created:
								lost_to_followup += 1
								lost_uhid_list.append(uhid)
							else:
								incompleted_measurement_count+=1
								incompleted_uhid_list.append(uhid)

						#Condition 2 : Subjects having less than 6 records,  Last PPG record is recorded one month ago from the current date.

						elif date_counts < 6 and date_counts != 0:

							org_date = list(set(ppg_recods))
							org_date = [datetime.strptime(date, "%Y-%m-%d") for date in org_date]

							# Sort in reverse order
							org_date.sort(reverse=True)
							last_ppg_created = org_date[0]

							if one_month_ago > last_ppg_created:
								lost_to_followup += 1
								lost_uhid_list.append(uhid)
							else:
								incompleted_measurement_count+=1
								incompleted_uhid_list.append(uhid)

						else:
							#if a subject have more than 2 visit then if they completed atleast each 3 recors for 2 visit it considerd as completed else its incompleted
							min_2date_count = 0
							for i in date_grouping:
								if i['count'] >= 3:
									min_2date_count+=1

								if min_2date_count <=2 :
									break

							if min_2date_count==2:
								completed_measurement_count += 1
								completed_uhid_list.append(uhid)
							else:
								incompleted_measurement_count += 1
								incompleted_uhid_list.append(uhid)
					else:
						completed_measurement_count += 1
						completed_uhid_list.append(uhid)

				except Exception as e:
					print("e:",e)

				if len(patient_data)==0:
					continue
				patient_data = patient_data[0]
				patient_gender = patient_data['gender']

				if patient_gender.lower() == 'male':
					total_male +=1
				else:
					total_female +=1


				if 35 <= int(patient_data['age']) <= 45:
					Group_35_45 += 1
				elif 46 <= int(patient_data['age']) <= 55:
					Group_46_55 += 1
				elif 56 <= int(patient_data['age']) <= 65:
					Group_56_65 += 1
				elif 66 <= int(patient_data['age']) <= 75:
					Group_66_75 += 1
				elif 75 <= int(patient_data['age']):
					Group_above_75 += 1
				elif 35 >= int(patient_data['age']):
					Group_below_35 += 1
			
				total_patient+=1

				get_health_data = database.get_patient_healthrecord(uhid)
				get_health_status = get_health_data[0]['health_status']

				if get_health_status == 'Prehypertension':
					prehypertension += 1
 
					if patient_gender == 'male':
						prehypertension_male +=1
					else:
						prehypertension_female +=1

				elif get_health_status == 'Stage 1 hypertension':
					hypertension_stage1 += 1
				
					if patient_gender == 'male':
						hypertension_stage1_male +=1
					else:
						hypertension_stage1_female +=1
				

				elif get_health_status == 'Stage 2 hypertension':
					hypertension_stage2 += 1
			
					if patient_gender == 'male':
						hypertension_stage2_male +=1
					else:
						hypertension_stage2_female +=1

				elif get_health_status == 'Normal':
					normal += 1
			
					if patient_gender == 'male':
						normal_male +=1
					else:
						normal_female +=1

			final_result = {"id":str(uuid.uuid4()),"created_at":datetime.now(),"modified_at":datetime.now(),"created_date":str(datetime.now().date()),"modified_date":str(datetime.now().date()),"uhid":uhid,"unique_measurement_count":completed_measurement_count,"repeat_measurement_count":incompleted_measurement_count,"total_episodes_count":total_measured_episodes_count,"total_patients_count":total_patient,"total_male_count":total_male,"total_female_count":total_female,"upcomimg_unique_measurement_count":incompleted_measurement_count,"prehypertension":prehypertension,"hypertension_stage1":hypertension_stage1,"hypertension_stage2":hypertension_stage2,
			"prehypertension_male":prehypertension_male,"prehypertension_female":prehypertension_female,"hypertension_stage1_male":hypertension_stage1_male,"hypertension_stage1_female":hypertension_stage1_female,"hypertension_stage2_male":hypertension_stage2_male,"hypertension_stage2_female":hypertension_stage2_female,"normal":normal,"normal_male":normal_male,"normal_female":normal_female,"group_35_45":Group_35_45,"group_46_55":Group_46_55,"group_56_65":Group_56_65,"group_66_75":Group_66_75,"lost_to_followup":lost_to_followup,"group_above_75":Group_above_75,"group_below_35":Group_below_35,"total_uhid_list":total_uhid_list,"completed_uhid_list":completed_uhid_list,"incompleted_uhid_list":incompleted_uhid_list,"lost_uhid_list":lost_uhid_list}
			print('finalresult>>',final_result)

			create_summary = database.create_measurement_summery_data(final_result)

			return "summery report created sucessfully"
		except Exception as ex:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
							f"line no: {exc_tb.tb_lineno} | {ex}")
			responseMsg = "Bad Request"
			return AppUtils.responseWithoutData(0, 400, responseMsg)

#################################################################
## Single BP estimation process
#################################################################
@service_url.route('/v2/process/estimation/patient/bp', methods=['POST'])
def process_estimation_of_bp():
	try:
		uhid="BH10017"
		if 'file' not in request.files:
			return AppUtils.responseWithoutData(0,400,"Missing file part")
		file = request.files['file']
		if file.filename == '':
			return AppUtils.responseWithoutData(0,400,"No file was selected for upload")
		if file:
			# save_path = 'D:/Farook/Projects/files_ppg/pre_denoise' + file.filename
			pre_denoise_dir='/var/www/html/ppg/exec/pre_denoise/'
			os.makedirs(pre_denoise_dir, exist_ok=True)
			save_path = '/var/www/html/ppg/exec/pre_denoise/' + file.filename
			print("save_path:",save_path)
			file.save(save_path)
		samplingf = request.form.get("samplingf", None)
		get_clib = database.get_ppg_cllib_data()
		if samplingf is None:
			samplingf = int(get_clib[0]['samplingf'])
		modelselect = request.form.get("modelselect", None)
		if modelselect is None:
			modelselect = str(get_clib[0]['modelType'])
		print("get_clib:",samplingf)
		record_name= request.form.get("record_name",None)
		# sampling_frequency= request.form.get("sampling_frequency",100)
		analysis_flag= request.form.get("analysis_flag",2)
		data_duration= request.form.get("data_duration",10)
		stitch_flag= int(request.form.get("stitch_flag",0))
		app_version= request.form.get("app_version",'1.0.2.64')
		app_version = version.parse(app_version)
		version_to_check = version.parse('1.0.2.64')

		print("record_name:",record_name)
		print("sampling_frequency:",samplingf)
		print("analysis_flag:",analysis_flag)
		print("data_duration:",data_duration)
		
		print("stitch_flag:",stitch_flag)
		print("app_version:",app_version)
		print("version_to_check:",version_to_check)

		# Set the LD_LIBRARY_PATH environment variable
		set_library = os.environ['LD_LIBRARY_PATH'] = '/home/PPG-Compute_v2/ppg/C-Library/exec/'
		post_denoise_dir='/var/www/html/ppg/exec/post_denoise/'
		os.makedirs(post_denoise_dir, exist_ok=True)

		print("set_library:",set_library)
		
		if app_version <= version_to_check: #old version
			print("old version")

			de_noise_flag= int(request.form.get("de_noise_flag",0))
			print("de_noise_flag:",de_noise_flag)
			command = ['/home/PPG-Compute_v2/ppg/C-Library/exec/libPPG_V1.2.2S', pre_denoise_dir+str(file.filename), post_denoise_dir, str(record_name), str(samplingf), str(analysis_flag), str(data_duration), str(de_noise_flag), str(stitch_flag)]

		else: #new version for new clib
			print("new version")

			de_noise_flag= int(request.form.get("de_noise_flag",1))
			print("de_noise_flag:",de_noise_flag)
			normalization_technique= int(request.form.get("normalization_technique",1))
			command = ['/home/PPG-Compute_v2/ppg/C-Library/exec/libPPG_V1.2.3S', '/var/www/html/ppg/exec/pre_denoise/'+str(file.filename), '/var/www/html/ppg/exec/post_denoise/', str(record_name), str(samplingf), str(analysis_flag), str(data_duration), str(de_noise_flag), str(stitch_flag), str(normalization_technique)]

		# command = ['/home/PPG-Python/ppg/C-Library/exec/libPPG_V1.2.3S', '/var/www/html/ppg/exec/pre_denoise/'+str(file.filename), '/var/www/html/ppg/exec/post_denoise/', str(record_name), str(sampling_frequency), str(analysis_flag), str(data_duration), str(de_noise_flag), str(stitch_flag),str(normalization_technique)]

		print("command:",command)

		result = subprocess.run(command, capture_output=True, text=True)
		print("result",result)
		denoise_json_file = '/var/www/html/ppg/exec/post_denoise/'+record_name+'_RecSession.json'
		denoise_json= '/ppg/exec/post_denoise/'+record_name+'_RecSession.json'
		denoise_csv= '/ppg/exec/post_denoise/'+record_name+'_DenoiseData.csv'


		print("denoise_json_file:",denoise_json_file)
		print("denoise_json:",denoise_json)
		print("denoise_csv:",denoise_csv)
		
		with open(denoise_json_file, 'r') as denoise_file:
			data = json.load(denoise_file)
			
		denoise_data = {"csv_file":denoise_csv,"json_file":denoise_json,"json_data":data}
		estimateFile='/home/PPG-Compute_v2/ppg_files/bp_estimation_files/'
		os.makedirs(estimateFile, exist_ok=True)
		save_path =estimateFile  + file.filename
		# file.save(save_path)
		if app_version <= version_to_check: #old version
			print("old version")#,save_path)

			print("request.files:",denoise_csv,type(denoise_csv))			
			# print("request.files['file']:",request.files['file'],type(request.files['file']))
			
			if denoise_csv:
				# save_path = 'F:/Office Work/Helyxon/Environment/PPG/' + file.filename
				save_path = '/home/PPG-Compute_v2/ppg_files/bp_estimation_files/' + denoise_csv
				denoise_csv.save(save_path)

			testid, extension = os.path.splitext(file.filename)
		else:
			print("file:")
			# save_path = '/home/PPG-Python/ppg_files/bp_estimation_files/' + file
			save_path = '/var/www/html/ppg/exec/post_denoise/' + denoise_csv
			print("new version")
			testid =  denoise_csv.replace(".csv_DenoiseData.csv", "")
			pass

		print("save_path",save_path)
		print("testid:",testid)

		get_clib = database.get_ppg_cllib_data()

		print("get_clib:",get_clib)
		patient_details= database.get_patient_demographics2(uhid,None)
		# modelselect= str(get_clib[0]['modelType'])

		# Read Reference SBP and DBP, Gender, HR
		try:
			referenceSBP = int(request.form.get("referenceSBP"))
		except:
			referenceSBP = 9998
		try:
			referenceDBP = int(request.form.get("referenceDBP"))
		except:
			referenceDBP = 9998
		try:
			heartRate = int(request.form.get("heartRate"))
			if heartRate == 0:
				heartRate = 9998 #change to string
		except:
			heartRate = 9998
		try:
			gender = request.form.get("gender")
		except:
			gender = 'N'

		try:
			sqiInfo = int(request.form.get("sqiInfo"))
		except:
			sqiInfo = 0

		bpLogicInfo = int(get_clib[0]['bpLogicInfo']) # 0-Perform old BP Correction
														# 1-Perform new BP Correction and also support old BP correction

		directionInfo = int(request.form.get("direction",0)) # 1-Resting Side BP
														# 2-Induced Low BP
														# 3-Induced High BP
														# 0-Direction not available.
		durationInfo = int(request.form.get("dataduration",0))# 10 or Multiple of 10s

		DataAlignmentFlag = int(get_clib[0]['DataAlignmentFlag'])

		SystolicPeaks = request.form.get("SystolicPeaks",0)

		SystolicPeaks = eval(SystolicPeaks)

		SystolicPeaks = [ int(x) for x in SystolicPeaks]

		# try:

		# 	samplingf= int(get_clib[0]['samplingf']) #int(request.form.get("samplingf"))
		# except Exception as e:
		# 	print("samplingf err:",samplingf)
		# 	samplingf = 100
		samplingf=int(samplingf)
		print("payload of onnx:",testid, save_path, samplingf, modelselect, referenceSBP, referenceDBP, heartRate, gender, sqiInfo, bpLogicInfo, directionInfo, durationInfo, DataAlignmentFlag, SystolicPeaks)
		result = onnx_model.estimateBPSingle(testid, save_path, samplingf, modelselect, referenceSBP, referenceDBP, heartRate, gender, sqiInfo, bpLogicInfo, directionInfo, durationInfo, SystolicPeaks, DataAlignmentFlag)
		onx_result = json.loads(result)
		print("onx_result",onx_result)
		# rawledfile = request.form.get("rawledfile", "")
		clibbpsys = request.form.get("clibbpsys", "")
		clibbpdia = request.form.get("clibbpdia", "")
		clib_jsonfile = request.form.get("clib_jsonfile", "")
		clib_ppgfile = request.form.get("clib_ppgfile", "")
		devicedetails = request.form.get("devicedetails", "")
		stitchflag = request.form.get("stitchflag", "")
		questions= request.form.getlist("questions") or []  # if it's a list/multi-select
		recordingstarttime = request.form.get("recordingstarttime", "")
		recordingendtime = request.form.get("recordingendtime", "")
		patient_details= database.get_patient_demographics(uhid,None,None,None)
		print("patient_details",patient_details)
		vital_details=database.get_patient_vitals(uhid)
		recordingduration=request.form.get("recordingduration", "")
		# get_profile[0]['gender']
		current_data={"id":str(uuid.uuid4()), 
		"created_at":datetime.now(), "modified_at":datetime.now(), 
		"uhid":request.form.get("uhid", "BH10017"),#p
		"patient_profile_id":patient_details[0]['_id'], 
		"bp":request.form.get("bp", ""), #
		"bp_sys":request.form.get("bp_sys", ""), 
		"bp_dia":request.form.get("bp_dia", ""), 
		"bp_measured_date":request.form.get("bp_measured_date", ""), #doubt
		"measured_date":datetime.now(),
		"ppg_file":str(file),#
		"posture":request.form.get("posture", ""), #p
		"activity":request.form.get("activity", ""),#p
		"heart_rate":vital_details[0]['heart_rate'], "temperature":vital_details[0]['temperature'],
	    "is_active":True,"refbp":vital_details[0]['bp'],
	    "corrected_bp":request.form.get("corrected_bp", ""),
	    "gtbp":request.form.get("bp", ""),#p
	    "estimated_bp":request.form.get("bp", ""),
		"sqstatus": request.form.get("sqstatus", ""),#p 
		"refbpsys": vital_details[0]['bp_sys'],#p
		"refbpdia": vital_details[0]['bp_dia'],#p
		"refbppr": request.form.get("refbppr", ""),#p json clip pulse
		"refgender": patient_details[0]['gender'],#p
		"refmodel": modelselect,#p
		"refmsamplingf": samplingf,#p
		"estimatedres": onx_result,#o
		"visitid": request.form.get("visitid", ""),#p
		"calibration":request.form.get("calibration", ""),
		"healthstatus":request.form.get("healthstatus", ""),
		"clibbpsys":clibbpsys,#me -json
		"clibbpdia":clibbpdia,#me -json
		"clib_jsonfile":denoise_json,#p
		"clib_ppgfile":denoise_csv,#p
		"devicedetails":devicedetails,#p
		"stitchflag": stitchflag,#p
		"questions":questions,#fail
		"recordingstarttime":recordingstarttime,#p
		"recordingduration":recordingduration,#p
		"recordingendtime":recordingendtime,#p
		"rawledfile":str(file)#p
		}
		print("c",current_data,uhid)
		create_data=database.create_patient_measurement(current_data)

		try:
			save_summery = execution_summary_report_calculation(uhid)
			print("ss",save_summery)
		except Exception as ex:
			exc_type, exc_obj, exc_tb = sys.exc_info()
			AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
							f"line no: {exc_tb.tb_lineno} | {ex}")
			responseMsg = "Bad Request"
			return AppUtils.responseWithoutData(0, 400, responseMsg)
		return AppUtils.responseWithData(1,200,"BP estimation process completed",onx_result)			
	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
						f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0, 400, responseMsg)	


#################################################################
## create role
#################################################################
@service_url.route("/v2/role/create", methods=['POST'])
def create_role():
	try:
		input_json = request.get_json(force=True)
		input_json["created_at"] = datetime.utcnow()
		input_json['modified_at'] = None
		create_data = database.create_role(input_json)
		return AppUtils.responseWithoutData(1, 201, "Role created successfully")
	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
						f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0, 400, responseMsg)
#################################################################
## Register admin users
#################################################################

@service_url.route("/v2/admin/create", methods=['POST'])
def create_admin_users():
	try:
		input_json = request.get_json(force=True)
		input_json["created_at"] = datetime.utcnow()
		input_json['modified_at'] = None
		input_json['server'] = input_json.get('server') or 'compute'
		hashedPwd = AuthHandler().getPasswordHash(password=input_json['password'])
		input_json['password']=hashedPwd
		get_role_data=database.get_role('admin')
		input_json['role_id']=str(get_role_data[0]['_id'])
		create_data = database.create_admin_data(input_json)
		return AppUtils.responseWithoutData(1, 201, "Admin created successfully")

	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
						f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0, 400, responseMsg)
	
#################################################################
## Login admin users Phase 2
#################################################################

@service_url.route("/v2/admin/login", methods=['POST'])
# @account
def admin_loginv2():
	try:
		input_json = request.get_json(force=True)
		check_admin=database.check_admin_credentials(input_json['user_name'])
		if check_admin==0:
			return AppUtils.responseWithoutData(0,404, "Admin not found")
		elif check_admin is not None and check_admin[0]['is_active'] == False:
			return AppUtils.responseWithoutData(0,403, "Admin is inactive.Please contact super admin")
		elif check_admin[0]['user_name'].strip() == "" or check_admin[0]['password'].strip() == "":
			return AppUtils.responseWithoutData(0,401, "Invalid credentials")
		verified = AuthHandler().verifyPassword(
            input_json['password'], check_admin[0]['password'])
		if not verified:
			return AppUtils.responseWithoutData(0,401, "Invalid credentials")			
		token = AuthHandler().encodeToken(check_admin[0]['user_name'])
		userResponsedata = check_admin[0]
		role_id_str = str(check_admin[0]['role_id'])
		role_info=database.get_role(None,ObjectId(role_id_str))
		userResponsedata['role_info']=role_info
		admin_details={
			'admin_data':userResponsedata,
			'token':token
		}
		return AppUtils.responseWithData(1,200, "Logged In successfully",admin_details )		
	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
                        f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0,400, responseMsg)

	
#################################################################
## Token creation for mobile app
#################################################################

@service_url.route("/v2/token/create", methods=['POST'])
# @account
def token_create():
	try:
		input_json = request.get_json(force=True)
		user_name=input_json.get('user_name')
		if user_name:
			create_token=AuthHandler().encodeToken(user_name)
			return AppUtils.responseWithData(1,200, "Token generated successfully",create_token )	
		else:
			return AppUtils.responseWithoutData(0,400, "Missing param user_name")		
	except Exception as ex:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		AppUtils.logger(__name__, AppUtils.getLogLevel().ERROR,
                        f"line no: {exc_tb.tb_lineno} | {ex}")
		responseMsg = "Bad Request"
		return AppUtils.responseWithoutData(0,400, responseMsg)