# Frontend example for file upload with AWS Lambda and FormData

The index.html file contains a simple form for uploading files to the S3 bucket. 
The form sends a POST request to the API Gateway and then to the Lambda function for processing the file upload.

The URL for sending the request should be obtained from the API Gateway and set in the form input with the label `URL:`.