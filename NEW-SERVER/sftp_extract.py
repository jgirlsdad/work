import pysftp,os,sys
import argparse

bic_etl_home = os.getenv('bic_etl_home')
sys.path.insert(0, os.path.join(bic_etl_home, 'general', 'scripts'))
import custom_log


parser = argparse.ArgumentParser(description='generic BIC transform script')
parser.add_argument('-t', '--title', help='-t is the dataset title')
parser.add_argument('-f', '--file',  help='File or folder to search in')
parser.add_argument('-o', '--output',  help='Output folder')
parser.add_argument('-n', '--local_file_name',  help='Name of local file (if different from server file name)')
parser.add_argument('-a', '--append',  help='Append file type')
parser.add_argument('-p', '--password',  help='Password')
parser.add_argument('-ho', '--host',  help='Host')
parser.add_argument('-u', '--username',  help='Username')
parser.add_argument('-k', '--private_key',  help='Private Key path')
parser.add_argument('-r', '--recent',  help='Take most recently modified file')
#parser.add_argument('-z', '--fuzzy',  help='Name given in -f argument has fuzzy match to source file name')
parser.add_argument('-c', '--current',  help='Take only file from current month')
parser.add_argument('-w','--week_current',  help='Take only file from current week')

args, leftovers = parser.parse_known_args()
w4x4="None"
logger2 = custom_log.setupNew(args.title)
logger2.info(f"Starting Extract for : {args.title}",extra={"s4x4":w4x4})

print(args)
if args.host is None:
    hostname="ftps.sos.state.co.us"
    username="xenbic"
    passwd=os.getenv('cdos_sftp_password')
else:
    hostname=args.host
file=args.file
output=args.output
outputFile=os.path.join(bic_etl_home,output)


try: 
    cinfo = {'host':hostname, 'username':username, 'password':passwd, 'port':22 }
    with pysftp.Connection(**cinfo) as sftp:
        sftp.get(file,outputFile)
        logger2.info(f"Extract Successful for {file} from {hostname} to {outputFile}",extra={"s4x4":w4x4})

        print(f"File {file} downloaded to {outputFile}")
except Exception as e:
    logger2.error(f"Extract FAILED for {file} from {hostname}",extra={"s4x4":w4x4})
    print(f"Error Extracting File: {e}")
    sys.exit(1)