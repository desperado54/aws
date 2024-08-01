import time
import traceback
import boto3
import logging
from collections import OrderedDict

logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('redshift-data')
BUCKET_URL = 's3://illest-core-refinery'
FILE_KEY = 'refined_route.csv'
TABLE = 'route(route,dt)'
IAM_ROLE = 'arn:aws:iam::992382776542:role/ILLEST-dev'

def lambda_handler(event, context):
    sql_statement=f"copy {TABLE} from '{BUCKET_URL}/{FILE_KEY}' iam_role '{IAM_ROLE}'"\
    " format as csv"\
    " ignoreheader 1"\
    " dateformat as 'yyyyMMdd'"
    
    execute_sql_data_api(client, "dev",'COPY',sql_statement,'default-workgroup',True)
    
def execute_sql_data_api(redshift_data_api_client, redshift_database_name, command, query, redshift_workgroup_name, isSynchronous):

    MAX_WAIT_CYCLES = 20
    attempts = 0
    # Calling Redshift Data API with executeStatement()
    res = redshift_data_api_client.execute_statement(
        Database=redshift_database_name, WorkgroupName=redshift_workgroup_name, Sql=query)
    query_id = res["Id"]
    desc = redshift_data_api_client.describe_statement(Id=query_id)
    query_status = desc["Status"]
    logger.info(
        "Query status: {} .... for query-->{}".format(query_status, query))
    done = False

    # Wait until query is finished or max cycles limit has been reached.
    while not done and isSynchronous and attempts < MAX_WAIT_CYCLES:
        attempts += 1
        time.sleep(1)
        desc = redshift_data_api_client.describe_statement(Id=query_id)
        query_status = desc["Status"]

        if query_status == "FAILED":
            raise Exception('SQL query failed:' +
                            query_id + ": " + desc["Error"])

        elif query_status == "FINISHED":
            logger.info("query status is: {} for query id: {} and command: {}".format(
                query_status, query_id, command))
            done = True
            # print result if there is a result (typically from Select statement)
            if desc['HasResultSet']:
                response = redshift_data_api_client.get_statement_result(
                    Id=query_id)
                logger.info(
                    "Printing response of {} query --> {}".format(command, response['Records']))
        else:
            logger.info(
                "Current working... query status is: {} ".format(query_status))

    # Timeout Precaution
    if done == False and attempts >= MAX_WAIT_CYCLES and isSynchronous:
        logger.info("Limit for MAX_WAIT_CYCLES has been reached before the query was able to finish. We have exited out of the while-loop. You may increase the limit accordingly. \n")
        raise Exception("query status is: {} for query id: {} and command: {}".format(
            query_status, query_id, command))

    return query_status