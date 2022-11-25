FROM public.ecr.aws/lambda/python:3.8

# Copy function code
COPY ./src ${LAMBDA_TASK_ROOT}

# Install the function's dependencies using file requirements.txt
# from your project folder.

COPY requirements.txt  .
RUN  pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
RUN  python3 -m nltk.downloader stopwords averaged_perceptron_tagger -d "${LAMBDA_TASK_ROOT}/nltk_data"


# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.lambda_handler" ]