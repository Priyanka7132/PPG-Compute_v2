# from pymongo import MongoClient
from pymongo.mongo_client import MongoClient
import urllib.request
import urllib.parse
from pymongo.server_api import ServerApi
from pymongo import ReturnDocument
from bson import ObjectId
from collections import Counter

#config for the Mongodb
client = MongoClient("mongodb://ec2-65-0-182-165.ap-south-1.compute.amazonaws.com:27017/") #stage
# client = MongoClient("mongodb://64.227.138.214:27017/") #production digitalocean

#credentials
# user_name = urllib.parse.quote_plus('info')
# password = urllib.parse.quote_plus('vU7mk2TboN0INBce')
# uri="mongodb+srv://"+user_name+":"+password+"@cluster0.hheqm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0&tls=true&tlsAllowInvalidCertificates=true"
# # Create a new client and connect to the server
# client = MongoClient(uri, server_api=ServerApi('1'))
 
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print("db er:",e)

def create_patient_demographics(input_data,return_id=False):
	db_name = 'ppg'
	collection_name = 'ppg_patient_demographics'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	if return_id:
		return create_record.inserted_id
	return 'success'


def create_patient_demographics_log(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_demographics_log'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def create_api_access_log(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_api_access_log'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def get_patient_demographics(uhid,phone_number,mr_number,user_name):
	dbname = 'ppg'
	collection_name = 'ppg_patient_demographics'
	db = client[dbname]
	collection = db[collection_name]

	if uhid != None and uhid != 'null':
		search_query = {"uhid":uhid, "is_active":True}
	elif mr_number != None and mr_number != 'null':
		search_query = {"mr_number":mr_number, "is_active":True}
	elif phone_number != None and phone_number != 'null':
		search_query = {"phone_number":phone_number, "is_active":True}
	elif user_name != None and user_name != 'null':
		search_query = {"user_name":user_name, "is_active":True}
	
	report_data = collection.find(search_query)
	arr_data = []
	for x in report_data:
		x['_id']=str(x['_id'])
		arr_data.append(x)

	return arr_data

def check_patient_demographics(uhid,phone_number):
	dbname = 'ppg'
	collection_name = 'ppg_patient_demographics'
	db = client[dbname]
	collection = db[collection_name]

	if uhid != None:
		search_query = {"uhid":uhid, "is_active":True}
	else:
		search_query = {"phone_number":phone_number, "is_active":True}

	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found


def check_patient_mr(mr_number):
	dbname = 'ppg'
	collection_name = 'ppg_patient_demographics'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"mr_number":mr_number,}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found


def last_patient_mr():
	dbname = 'ppg'
	collection_name = 'ppg_patient_demographics'
	db = client[dbname]
	collection = db[collection_name]

	result = list(collection.find().sort('created_at', -1).limit(1))

	try:
		last_patient_mr=result[0]['mr_number']
	except:
		last_patient_mr=None


	return last_patient_mr


def update_patient_demographics(input_data):
	dbname = 'ppg'
	collection_name = 'ppg_patient_demographics'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"id":input_data["id"]}
	newValues = {"$set": {"modified_at":input_data['modified_at'], "first_name":input_data['first_name'], "last_name":str(input_data['last_name']), "phone_number":str(input_data['phone_number']), "email":str(input_data['email']), "gender":str(input_data['gender']), "dob":str(input_data['dob']),"age_in_days":input_data['age_in_days'],"avatar": input_data['avatar'],"user_name": input_data['user_name'],"age":input_data['age'],"mr_number":input_data['mr_number'],"address":input_data['address'],"ethnicity":input_data['ethnicity'],"country_code":input_data['country_code'],"notes":input_data['notes']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status


def create_operator_demographics(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_operator_demographics'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def get_operator_demographics(user_name,phone_number):
	dbname = 'ppg'
	collection_name = 'ppg_operator_demographics'
	db = client[dbname]
	collection = db[collection_name]

	if user_name != None:
		search_query = {"user_name":user_name.lower(), "is_active":True}
	else:
		search_query = {"phone_number":phone_number, "is_active":True}

	profile_data = collection.find(search_query,{'_id':0})
	
	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data

	return 'success'

def check_operator_demographics(user_name,phone_number):
	dbname = 'ppg'
	collection_name = 'ppg_operator_demographics'
	db = client[dbname]
	collection = db[collection_name]

	if user_name != None:
		search_query = {"user_name":user_name.lower(), "is_active":True}
	else:
		search_query = {"phone_number":phone_number, "is_active":True}

	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found


def update_operator_demographics(input_data):
	dbname = 'ppg'
	collection_name = 'ppg_operator_demographics'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"id":input_data["id"],"user_name":(input_data["user_name"]).lower()}
	newValues = {"$set": {"modified_at":input_data['modified_at'], "first_name":input_data['first_name'], "last_name":str(input_data['last_name']), "phone_number":str(input_data['phone_number']), "email":str(input_data['email']), "gender":str(input_data['gender']), "dob":str(input_data['dob']), "avatar": input_data['avatar'], "department": input_data['department'],"user_type":(input_data['user_type']).lower() }}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status


def update_operator_profileusername(input_data):
	dbname = 'ppg'
	collection_name = 'ppg_operator_demographics'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"id":input_data["id"],"user_name":input_data['old_user_name'] }
	newValues = {"$set": {"modified_at":input_data['modified_at'], "user_name":input_data['new_user_name'] }}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status

def store_operator_credentials(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_operator_credentials'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def update_operator_name(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_operator_credentials'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"operator_profile_id":input_data['id'],"user_name":input_data['old_user_name'] }
	newValues = {"$set": {"user_name":input_data['new_user_name'] }}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status


def validate_operator_credentials(user_name,password):
	db_name = 'ppg'
	collection_name = 'ppg_operator_credentials'
	db = client[db_name]
	collection = db[collection_name]
	search_query = {"user_name":user_name, "password":password}

	result = collection.find(search_query,{'_id':0})
	
	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found

def save_operator_login_details(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_operator_login'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def create_patient_healthrecord(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_healthrecord'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def get_patient_healthrecord(uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_healthrecord'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"uhid":uhid, "is_active":True}
	profile_data = collection.find(search_query,{'_id':0})
	
	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data

	return 'success'

def update_patient_healthrecord(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_healthrecord'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"uhid":input_data['uhid'] }
	newValues = {"$set": {"health_status":input_data['health_status'],'medical_history':input_data['medical_history'],"consent_obtained":input_data['consent_obtained'],"calibration_needed":input_data['calibration_needed'],'calibration_protocol':input_data['calibration_protocol'],"chief_complaint":input_data['chief_complaint'] }}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status


def check_patient_healthrecord(uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_healthrecord'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"uhid":uhid, "is_active":True}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found


def create_patient_calibration_record(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_calibration_record'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'


def check_patient_calibration(uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_calibration_record'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"uhid":uhid}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found

def check_patient_calibration_record(input_data):
	dbname = 'ppg'
	collection_name = 'ppg_patient_calibration_record'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"uhid":input_data['uhid'],"posture":input_data['posture'],"activity":input_data['activity'], "is_active":True}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found

def update_patient_calibration_record(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_calibration_record'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"uhid":input_data['uhid'],"patient_profile_id":input_data['patient_profile_id'],"posture":input_data['posture'],"activity":input_data['activity'] }

	newValues = {"$set": {"modified_at":input_data['modified_at'],"measured_date":input_data['measured_date'],"bp1_sys":input_data['bp1_sys'],"bp1_dia":input_data['bp1_dia'],"bp1_measured_date":input_data['bp1_measured_date'],"bp2_sys":input_data['bp2_sys'],"bp2_dia":input_data['bp2_dia'],"bp2_measured_date":input_data['bp2_measured_date'],"calibration_status":input_data['calibration_status'],"bp1":input_data['bp1'],"bp2":input_data['bp2'],"ppg1_file":input_data['ppg1_file'],"ppg2_file":input_data['ppg2_file']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status


def get_patient_calibration_record(uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_calibration_record'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"uhid":uhid, "is_active":True}
	profile_data = collection.find(search_query,{'_id':0})
	
	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data

	return 'success'

def create_operator_sitedetails(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_operator_sitedetails'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'


def create_patient_sitedetails(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_sitedetails'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'


def check_operator_sitedetails(operator_profile_id):
	dbname = 'ppg'
	collection_name = 'ppg_operator_sitedetails'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"operator_profile_id":operator_profile_id,"is_active":True}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found

def check_patient_sitedetails(patient_profile_id):
	dbname = 'ppg'
	collection_name = 'ppg_patient_sitedetails'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"patient_profile_id":patient_profile_id,"is_active":True}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found

def get_operator_sitedetails(operator_profile_id):
	dbname = 'ppg'
	collection_name = 'ppg_operator_sitedetails'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"operator_profile_id":operator_profile_id,"is_active":True}
	profile_data = collection.find(search_query,{'_id':0})
	
	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data

	return 'success'


def get_patient_sitedetails(patient_profile_id):
	dbname = 'ppg'
	collection_name = 'ppg_patient_sitedetails'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"patient_profile_id":patient_profile_id,"is_active":True}
	profile_data = collection.find(search_query,{'_id':0})
	
	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data

	return 'success'


def update_operator_sitedetails(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_operator_sitedetails'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"operator_profile_id":input_data['operator_profile_id'],"is_active":True}

	newValues = {"$set": {"modified_at":input_data['modified_at'],"device_details":input_data['device_details'],"device_address":input_data['device_address'],"device_brand":input_data['device_brand'],"site_name":input_data['site_name']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status



def update_patient_sitedetails(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_sitedetails'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"patient_profile_id":input_data['patient_profile_id'],"is_active":True}

	newValues = {"$set": {"modified_at":input_data['modified_at'],"device_details":input_data['device_details'],"device_address":input_data['device_address'],"device_brand":input_data['device_brand'],"site_name":input_data['site_name'],"operator_name":input_data['operator_name']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status


def create_patientvitals(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_vitals'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'


def check_patient_vitals(uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_vitals'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"uhid":uhid, "is_active":True}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found

def get_patient_vitals(uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_vitals'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"uhid":uhid, "is_active":True}
	profile_data = collection.find(search_query,{'_id':0})
	
	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data

	return 'success'


def update_patient_vitals(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_vitals'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"uhid":input_data['uhid'],"id":input_data['id'] }

	newValues = {"$set": {"modified_at":input_data['modified_at'],"bp":input_data['bp'], "bp_sys":input_data['bp_sys'], "bp_dia":input_data['bp_dia'], "heart_rate":input_data['heart_rate'], "temperature":input_data['temperature'],"weight":input_data['weight'],"height":input_data['height'],"respiratory_rate":input_data['respiratory_rate'],"wrist_size":input_data['wrist_size'],"bp_dia2":input_data['bp_dia2'],"bp_sys2":input_data['bp_sys2'],"bp2":input_data['bp2']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status


def create_patient_measurement(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_measurement'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'


def check_patient_measurement(uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_measurement'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"uhid":uhid, "is_active":True}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found


def get_patient_measurement(uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_measurement'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"uhid":uhid, "is_active":True}
	profile_data = collection.find(search_query,{'_id':0})
	
	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data

	return 'success'

def get_patient_measurement_report(from_date, to_date, uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_measurement'
	db = client[dbname]
	collection = db[collection_name]

	if uhid != None:
		search_query = {"uhid":uhid, "is_active":True, "measured_date": {"$gte": from_date, "$lte": to_date}}
	else:
		search_query = {"is_active":True, "measured_date": {"$gte": from_date, "$lte": to_date}}

	report_data = collection.find(search_query, {'_id': 0})
	arr_data = []
	for x in report_data:
		x['estimatedpr']=x['heart_rate']
		del(x['heart_rate'])
		arr_data.append(x)

	return arr_data

def get_measurement_patient_list(from_date, to_date):
	dbname = 'ppg'
	collection_name = 'ppg_patient_measurement'
	db = client[dbname]
	collection = db[collection_name]
	list_data =  collection.distinct("uhid", {"measured_date": {"$gte": from_date, "$lte": to_date}})
	return list_data

def update_patient_measurement(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_measurement'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"uhid":input_data['uhid'],"id":input_data['id'] }

	newValues = {"$set": {"modified_at":input_data['modified_at'],"measured_date":input_data['measured_date'],"bp":input_data['bp'],"bp_sys":input_data['bp_sys'],"bp_dia":input_data['bp_dia'],"bp_measured_date":input_data['bp_measured_date'],"ppg_file":input_data['ppg_file'],"posture":input_data['posture'],"activity":input_data['activity'],"heart_rate":input_data['heart_rate'],"temperature":input_data['temperature'],"gtbp":input_data['gtbp'],"estimated_bp":input_data['estimated_bp'],
			"sqstatus": input_data['sqstatus'],
			"refbpsys": input_data['refbpsys'],
			"refbpdia": input_data['refbpdia'],
			"refbppr": input_data['refbppr'],
			"refgender": input_data['refgender'],
			"refmodel": input_data['refmodel'],
			"refmsamplingf": input_data['refmsamplingf'],
			"estimatedres": input_data['estimatedres'],
			"visitid": input_data['visitid'],
			"calibration":input_data['calibration'],
			"healthstatus":input_data['healthstatus'],
			"stitchflag":input_data['stitchflag'],
			"questions":input_data['questions'],
			"recordingstarttime":input_data['recordingstarttime'],
			"recordingduration":input_data['recordingduration'],
			"recordingendtime":input_data['recordingendtime'],
			"rawledfile":input_data['rawledfile'],}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status



def create_patient_profile_measurement(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_profile_measurement'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'


def check_patient_profile_measurement(uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_profile_measurement'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"uhid":uhid, "is_active":True}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found


def get_patient_profile_measurement(uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_profile_measurement'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"uhid":uhid, "is_active":True}
	profile_data = collection.find(search_query,{'_id':0})
	
	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data

	return 'success'

def update_patient_profile_measurement(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_profile_measurement'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"uhid":input_data['uhid'],"id":input_data['id'] }

	newValues = {"$set": {"modified_at":input_data['modified_at'],"measured_date":input_data['measured_date'],"bp":input_data['bp'],"bp_sys":input_data['bp_sys'],"bp_dia":input_data['bp_dia'],"bp_measured_date":input_data['bp_measured_date'],"ppg_file":input_data['ppg_file'],"posture":input_data['posture'],"activity":input_data['activity'],"heart_rate":input_data['heart_rate'],"temperature":input_data['temperature']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status



def create_bearer_token(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_bearer_token'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'


def check_bearer_token(account_id,secrect_key):
	dbname = 'ppg'
	collection_name = 'ppg_bearer_token'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"account_id":account_id,"secrect_key":secrect_key, "is_active":True}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found


def get_bearer_token(account_id,secrect_key):
	dbname = 'ppg'
	collection_name = 'ppg_bearer_token'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"account_id":account_id,"secrect_key":secrect_key, "is_active":True}
	profile_data = collection.find(search_query,{'_id':0})

	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data


def create_calibrationprotocol(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_calibration_protocol'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def get_calibrationprotocol(query_type,user_name,calibration_id):
	dbname = 'ppg'
	collection_name = 'ppg_calibration_protocol'
	db = client[dbname]
	collection = db[collection_name]

	if query_type==1:
		search_query = {"user_name":user_name}
	else:
		search_query = {"id":calibration_id}

	result = collection.find(search_query,{'_id':0})

	final_result = []
	for i in result:
		final_result.append(i)

	return final_result

def update_calibrationprotocol(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_calibration_protocol'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"id":input_data['id'],"user_name":input_data['user_name'] }

	newValues = {"$set": {"modified_at":input_data['modified_at'],"calibration_protocol_name":input_data['calibration_protocol_name'],"calibration":input_data['calibration']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status


def check_calibrationprotocol(user_name,calibration_id):
	dbname = 'ppg'
	collection_name = 'ppg_calibration_protocol'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"user_name":user_name,"id":calibration_id}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found

def create_adminsite(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_site_list'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def get_adminsite():
	dbname = 'ppg'
	collection_name = 'ppg_site_list'
	db = client[dbname]
	collection = db[collection_name]

	list_data = collection.find({},{'_id':0})
	arr_data = []
	for x in list_data:
		arr_data.append(x)

	return arr_data

def update_adminsite(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_site_list'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"id":input_data['id']}

	newValues = {"$set": {"modified_at":input_data['modified_at'],"site_name":input_data['site_name'],"site_address":input_data['site_address']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status



def create_adminprotocol(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_admin_calibration_protocol'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def get_adminprotocol(query_type,user_name,calibration_id):
	dbname = 'ppg'
	collection_name = 'ppg_admin_calibration_protocol'
	db = client[dbname]
	collection = db[collection_name]

	if query_type==1:
		search_query = {"user_name":user_name}
	else:
		search_query = {"id":calibration_id}

	result = collection.find(search_query,{'_id':0})

	final_result = []
	for i in result:
		final_result.append(i)

	return final_result

def update_adminprotocol(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_admin_calibration_protocol'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"id":input_data['id'],"user_name":input_data['user_name'] }

	newValues = {"$set": {"modified_at":input_data['modified_at'],"calibration_protocol_name":input_data['calibration_protocol_name'],"calibration":input_data['calibration']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status


def check_adminprotocol(user_name,calibration_id):
	dbname = 'ppg'
	collection_name = 'ppg_admin_calibration_protocol'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"user_name":user_name,"id":calibration_id}
	result = collection.find(search_query,{'_id':0})

	is_Found = 0
	for i in result:
		is_Found = 1

	return is_Found


def get_operator_list():
	dbname = 'ppg'
	collection_name = 'ppg_operator_demographics'
	db = client[dbname]
	collection = db[collection_name]

	profile_data = collection.find({"user_type":"operator","is_active":True},{'_id':0})
	
	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data

def create_otafile(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_otafile'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def get_otafile(folder_name):
	db_name = 'ppg'
	collection_name = 'ppg_otafile'
	db = client[db_name]
	collection = db[collection_name]
	arr_data = collection.find({"folder_name":folder_name},{'_id':0})
	
	final_data = []
	for x in arr_data:
		final_data.append(x)

	return final_data


def check_otafile(folder_name):
	db_name = 'ppg'
	collection_name = 'ppg_otafile'
	db = client[db_name]
	collection = db[collection_name]
	arr_data = collection.find({"folder_name":folder_name},{'_id':0})
	
	status=False
	for x in arr_data:
		status=True

	return status

def get_latest_otafile():
	db_name = 'ppg'
	collection_name = 'ppg_otafile'
	db = client[db_name]
	collection = db[collection_name]
	arr_data = list(collection.find().sort('created_at', -1).limit(1))
	return arr_data

def get_latest_otafile_list():
	db_name = 'ppg'
	collection_name = 'ppg_otafile'
	db = client[db_name]
	collection = db[collection_name]
	arr_data = list(collection.find())
	return arr_data


def get_patient_measurement_dump():
	dbname = 'ppg'
	collection_name = 'ppg_patient_measurement'
	db = client[dbname]
	collection = db[collection_name]

	profile_data = collection.find({"clibbpdia": {"$exists": False},"clibbpsys": {"$exists": False}})

	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data

def get_patient_demographics_dump(profile_id):
	dbname = 'ppg'
	collection_name = 'ppg_patient_demographics'
	db = client[dbname]
	collection = db[collection_name]

	result = collection.find({"id":profile_id, "is_active":True},{'_id':0})
	final_result=[]
	for i in result:
		final_result.append(i)

	return final_result


def update_patient_measurement_dump(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_measurement'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"patient_profile_id":input_data['patient_profile_id'],"id":input_data['id'] }

	newValues = {"$set": {"clibbpsys": input_data['clibbpsys'],"clibbpdia": input_data['clibbpdia'],"clib_jsonfile":input_data['clib_jsonfile'],"clib_ppgfile":input_data['clib_ppgfile']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status

def create_encrtpted_data(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_encrtpted_data'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'


def get_encrtpted_data(input_data):
	dbname = 'ppg'
	collection_name = 'ppg_encrtpted_data'
	db = client[dbname]
	collection = db[collection_name]

	result = collection.find({"name":input_data},{'_id':0})
	final_result=[]
	for i in result:
		final_result.append(i)

	return final_result

def generate_uhid_safe():
	db_name = 'ppg'
	db=client[db_name]
	collection_name = 'ppg_patient_demographics'	
	result =db.counters.find_one_and_update(
		{"_id": "uhid"},
		{"$inc": {"seq": 1}},
		upsert=True,
		return_document=ReturnDocument.AFTER
	)
	return f"BH1{str(result['seq']).zfill(4)}"

##Login patient profile phase2

def check_user_credentials(user_name):
    dbname = 'ppg'
    collection_name = 'ppg_patient_demographics'
    db = client[dbname]
    collection = db[collection_name]

    if user_name is None:
        return 0  # Invalid input

    search_query = {
        "user_name": user_name,
        "is_active": True
    }

    result = list(collection.find(search_query, {'_id': 0}))

    if result:
        return result  # return list of matched user(s) without _id
    else:
        return 0  # no match found

#Insert device data
def create_device_data(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_device_info'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def get_device_data(id=None):
	db_name = 'ppg'
	collection_name = 'ppg_device_info'
	db = client[db_name]
	collection = db[collection_name]
	if id:
		result = collection.find_one({"_id": id}, {'_id': 0})
		return result 
	else:
		return list(collection.find({}, {'_id': 0})) 
	
##Update device data
def update_device_data(input_json):
    db_name = 'ppg'
    collection_name = 'ppg_device_info'
    db = client[db_name]
    collection = db[collection_name]

    device_id_str = input_json.get('id')
    
    if device_id_str:
        device_info_id = ObjectId(device_id_str)

        # Remove 'id' from the update payload to avoid trying to overwrite _id
        update_data = input_json.copy()
        update_data.pop('id', None)

        # Perform the update (partial update)
        result = collection.update_one(
            {'_id': device_info_id},
            {'$set': update_data}
        )

        if result.modified_count > 0:
            return {"status": 1, "message": "Device updated successfully"}
        else:
            return {"status": 0, "message": "No changes made or device not found"}
    else:
        return {"status": 0, "message": "Missing device ID"}


#update patient profile for version 2
	
def update_patient_demographicsv2(input_data):
	dbname = 'ppg'
	collection_name = 'ppg_patient_demographics'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"_id":input_data["id"]}
	newValues = {"$set": {"modified_at":input_data['modified_at'], "first_name":input_data['first_name'],"gender":str(input_data['gender']),"age":input_data['age'],"skin_tone":input_data['skin_tone'],"is_active":input_data['is_active'] if input_data.get('is_active') else True,
}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status

##update patient_demographics log
def update_patient_demographics_logv2(input_data):
	dbname = 'ppg'
	collection_name = 'ppg_patient_demographics_log'
	db = client[dbname]
	collection = db[collection_name]

	search_query = {"id":input_data["id"]}
	newValues = {"$set": {"modified_at":input_data['modified_at'], "first_name":input_data['first_name'],"gender":str(input_data['gender']),"age":input_data['age'],"skin_tone":input_data['skin_tone']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status

##update patient health record
def update_patient_healthrecordv2(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_healthrecord'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"uhid":input_data['uhid'] }
	newValues = {"$set": {"modified_at":input_data['modified_at'] }}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status

##update patient vitals
def update_patient_vitalsv2(input_data,id=None):
	db_name = 'ppg'
	collection_name = 'ppg_patient_vitals'
	db = client[db_name]
	collection = db[collection_name]
    
	if id is None:
		search_query = {"uhid":input_data['uhid'] }
	else:
		search_query = {"uhid":input_data['uhid'],"id":input_data['id'] }

	newValues = {"$set": {"modified_at":input_data['modified_at'],"bp":input_data['bp'], "bp_sys":input_data['bp_sys'], "bp_dia":input_data['bp_dia'], "heart_rate":input_data['heart_rate'],"is_active":input_data['is_active']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status


def create_admin_data(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_admin_users'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'

def create_role(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_role'
	db = client[db_name]
	collection = db[collection_name]
	create_record = collection.insert_one(input_data)
	return 'success'


def get_role(input_data=None,role_id=None):
	dbname = 'ppg'
	collection_name = 'ppg_role'
	db = client[dbname]
	collection = db[collection_name]
	if role_id is not None:
		search_query = {"_id":role_id, "is_active":True}
		profile_data = collection.find(search_query,{'_id': 0})
	else:
		search_query = {"name":input_data, "is_active":True}
		profile_data = collection.find(search_query)
	
	arr_data = []
	for x in profile_data:
		arr_data.append(x)

	return arr_data

#admin credential check
def check_admin_credentials(user_name):
    dbname = 'ppg'
    collection_name = 'ppg_admin_users'
    db = client[dbname]
    collection = db[collection_name]

    if user_name is None:
        return 0  # Invalid input

    search_query = {
        "user_name": user_name,
        "is_active": True
		# "server":"compute"
    }

    result = list(collection.find(search_query, {'_id': 0}))

    if result:
        return result  # return list of matched user(s) without _id
    else:
        return 0  # no match found
	

##Get Admin Data
def get_admin_data(id=None):
	db_name = 'ppg'
	collection_name = 'ppg_admin_users'
	db = client[db_name]
	collection = db[collection_name]
	if id:
		result = collection.find_one({"_id": id}, {'_id': 0})
		return result 
	else:
		return list(collection.find({}, {'_id': 0})) 
	
##Inactive Patient Profile
def inactive_patient_profile(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_demographics'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"uhid":input_data['uhid'] }
	newValues = {"$set": {"modified_at":input_data['modified_at'],"is_active":input_data['is_active']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status

##Inactive Patient vitals
def inactive_patient_vitals(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_vitals'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"uhid":input_data['uhid'] }
	newValues = {"$set": {"modified_at":input_data['modified_at'],"is_active":input_data['is_active']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status

##Inactive Patient health record
def inactive_patient_health_record(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_patient_healthrecord'
	db = client[db_name]
	collection = db[collection_name]

	search_query = {"uhid":input_data['uhid'] }
	newValues = {"$set": {"modified_at":input_data['modified_at'],"is_active":input_data['is_active']}}

	result = collection.update_one(search_query,newValues)

	if result.matched_count > 0:
		status = 1  #document updated
	else:
		status = 0  #no matching document found

	return status


def get_patient_demographicsv2(skip=0, limit=10):
	dbname = 'ppg'
	collection = client[dbname]['ppg_patient_demographics']

	# Query for active patients
	query = {"is_active": True,"version":2}

	# Total count
	total_count = collection.count_documents(query)

	# Fetch paginated results
	cursor = collection.find(query).skip(skip).limit(limit)
	result = []

	for doc in cursor:
		doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
		result.append(doc)

	return result, total_count

def get_ppg_cllib_data():
	db_name = 'ppg'
	collection_name = 'ppg_clib_data'
	db = client[db_name]
	collection = db[collection_name]
	result = collection.find()
	final_result=[]
	for i in result:
		final_result.append(i)
	return final_result

def get_measurement_date_list(uhid):
	dbname = 'ppg'
	collection_name = 'ppg_patient_measurement'
	db = client[dbname]
	collection = db[collection_name]

	list_data =  collection.find({"uhid": uhid})	
	total_dump = list(list_data)


	list_data_count=len(list(list_data))

	completed_patient=False

	dates = [entry["created_at"].strftime('%Y-%m-%d') for entry in total_dump]
	date_counts = Counter(dates)
	result = [{"date": date, "count": count} for date, count in date_counts.items()]

	#unique_measurement_status == True: #completed all count -- completed_patient true
	#unique_measurement_status == False: #completed half and followup needed -- completed_patient false

	# each visit has 3 record if total is 6 then it completed, else it should comes under followup needed eg. for consicutive days of 2,2,2, not completed
	# first visit alone has 6 record if total is 6  -- followup needed

	if len(result) == 1: #same date
		completed_patient=False
		
	else: #different date
		get_visit_count = 3#int(get_patient_healthrecord(uhid)[0]['observation_per_visit'])		
		min_2date_count = 0
		for i in result:
			if int(i['count']) >= get_visit_count:
				
				if min_2date_count <= 2:
					min_2date_count += 1
					completed_patient=True
					break
			else:
				completed_patient=False
				break

	list_data_count = len(total_dump)

	return completed_patient,list_data_count,dates,result

def create_measurement_summery_data(input_data):
	db_name = 'ppg'
	collection_name = 'ppg_measurement_summery'
	db = client[db_name]
	collection = db[collection_name]

	result = collection.find({"uhid":input_data['uhid']},{'_id':0})
	final_result=[]
	result_len = list(result)

	if len(result_len) != 0:
		#update
		search_query = {"uhid":input_data["uhid"]}
		new_values = {
			"$set": {
				"modified_at": input_data["modified_at"],
				"modified_date": input_data["modified_date"],
				"unique_measurement_count": input_data["unique_measurement_count"],
				"repeat_measurement_count": input_data["repeat_measurement_count"],
				"total_episodes_count": input_data["total_episodes_count"],
				"total_patients_count": input_data["total_patients_count"],
				"total_male_count": input_data["total_male_count"],
				"total_female_count": input_data["total_female_count"],
				"upcomimg_unique_measurement_count": input_data["upcomimg_unique_measurement_count"],
				"prehypertension": input_data["prehypertension"],
				"hypertension_stage1": input_data["hypertension_stage1"],
				"hypertension_stage2": input_data["hypertension_stage2"],
				"prehypertension_male": input_data["prehypertension_male"],
				"prehypertension_female": input_data["prehypertension_female"],
				"hypertension_stage1_male": input_data["hypertension_stage1_male"],
				"hypertension_stage1_female": input_data["hypertension_stage1_female"],
				"hypertension_stage2_male": input_data["hypertension_stage2_male"],
				"hypertension_stage2_female": input_data["hypertension_stage2_female"],
				"normal": input_data["normal"],
				"normal_male": input_data["normal_male"],
				"normal_female": input_data["normal_female"],
				"group_35_45": input_data["group_35_45"],
				"group_46_55": input_data["group_46_55"],
				"group_56_65": input_data["group_56_65"],
				"group_66_75": input_data["group_66_75"],
				"lost_to_followup": input_data["lost_to_followup"],
				"group_above_75": input_data["group_above_75"],
				"group_below_35": input_data["group_below_35"],
				"total_uhid_list": input_data["total_uhid_list"],
				"completed_uhid_list": input_data["completed_uhid_list"],
				"incompleted_uhid_list": input_data["incompleted_uhid_list"],
				"lost_uhid_list": input_data["lost_uhid_list"]
				}
			}

		result = collection.update_one(search_query,new_values)

	else:
		#create
		create_record = collection.insert_one(input_data)
	return 'success'

## GET patient datas for version 2
def get_patient_demographics2(uhid,user_name):
	dbname = 'ppg'
	collection_name = 'ppg_patient_demographics'
	db = client[dbname]
	collection = db[collection_name]

	if uhid != None and uhid != 'null':
		search_query = {"uhid":uhid, "is_active":True,"version":2}
	elif user_name != None and user_name != 'null':
		search_query = {"user_name":user_name, "is_active":True,"version":2}
	
	report_data = collection.find(search_query)
	arr_data = []
	for x in report_data:
		x['_id']=str(x['_id'])
		arr_data.append(x)

	return arr_data