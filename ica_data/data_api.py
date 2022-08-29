import os
import requests
import getpass
import icav2
from icav2.api import project_data_api

class DataApi:
    def __init__(self, project_id=None, tenant=None):
        self.project_id = os.environ['ICA_PROJECT'] if project_id == None else project_id
        self.tenant = 'sequencebio' if tenant == None else tenant
        self.api_client = None

    def __authenticate(self):
        """Authenticate with ICA API."""
        if self.api_client:
            return

        username = input("ICA Username")
        password = getpass.getpass("ICA Password")

        url = os.environ['ICA_URL'] + '/rest/api/tokens'
        auth_request = requests.post(url, data={}, auth=(username, password), params={'tenant': self.tenant})

        if auth_request.status_code == 200:
            configuration = icav2.Configuration(
                host = os.environ['ICA_URL'] + '/rest',
                access_token = str(auth_request.json()["token"])
            )
            ica_client = icav2.ApiClient(configuration, header_name="Content-Type", header_value="application/vnd.illumina.v3+json")
            self.api_client = project_data_api.ProjectDataApi(ica_client)
            print("Authentication successful.")
        else:
            print(f"Error authenticating to {os.environ['ICA_URL']}")
            print(f"Response: {auth_request.status_code}")

    def list(self, page_size=50, page_offset=0, sort="path"):
        """List all data objects in the ICA project directory."""
        # TODO: Change this to return a list of data objects rather than just print stuff out (maybe have an argument to print? or a separate method to print?)
        # TODO: Add args (ideally a single pass-through arg) for the various filtering options so folks can filter by path, etc.

        self.__authenticate()

        try:
            project_data_page = self.api_client.get_project_data_list(project_id=self.project_id, page_size=str(page_size), page_offset=str(page_offset), sort=sort)
            while len(project_data_page.items) > 0:
                pprint(project_data_page)
                page_offset = page_offset + page_size
                project_data_page = self.api_client.get_project_data_list(project_id=self.project_id, page_size=str(page_size), page_offset=str(page_offset), sort=sort)
        except icav2.ApiException as e:
            print(f"Exception when listing project data: {e}")

    def upload(self, file_path, upload_path=None):
        """Upload a file to the ICA project bucket."""
        # TODO: Sort out the issue of overwriting.

        self.__authenticate()

        upload_path = file_path if upload_path == None else upload_path

        # Create data element in the project
        empty_object = icav2.model.create_data.CreateData(name=upload_path, data_type="FILE")

        try:
            data_object = self.api_client.create_data_in_project(self.project_id, create_data=empty_object)
            file_id = data_object.data.id
        except icav2.ApiException as e:
            print(f"Exception when creating the data object: {e}")

        try:
            upload = self.api_client.create_upload_url_for_data(project_id=self.project_id, data_id=file_id)
            data = open(file_path, 'r').read()
            requests.put(upload.url, data=data)
        except icav2.ApiException as e:
            print(f"Exception when uploading file: {e}")


    def download(self, file_path, download_path=None):
        """Download a file from the ICA project bucket."""

        self.__authenticate()

        try:
            file_id = self.find(file_path)

            # Download file
            download = self.api_client.create_download_url_for_data(project_id=self.project_id, data_id=file_id)
            download_request = requests.get(download.url)

            # Write file to local filesystem.
            temp_filename = f"/tmp/{file_path}" if download_path == None else f"{download_path}/{file_path}"
            open(temp_filename, 'wb').write(download_request.content)
            print(f"File downloaded to: {temp_filename}")

            return temp_filename
        except icav2.ApiException as e:
            print(f"Exception when downloading file: {e}")

    def delete(self, file_id = None, file_path = None):
        """"Delete a single file."""

        self.__authenticate()

        try:
            data_id = self.find(file_path) if file_id == None else file_id
            result = self.api_client.delete_data(project_id=self.project_id, data_id=data_id)
            print(f"result: {result}")
        except icav2.ApiException as e:
            print(f"Exception when deleting file: {e}")

    def find(self, file_path):
        """"Find a single file in an ICA project."""

        self.__authenticate()

        try:
            path = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            results = self.api_client.get_project_data_list(project_id=self.project_id, file_path=[path], filename=[filename], filename_match_mode="EXACT", type="FILE")
            file_id = results.items[0].data.id
            print(f"File ID: {file_id}")

            return file_id
        except icav2.ApiException as e:
            print(f"Exception when trying to find file: {e}")