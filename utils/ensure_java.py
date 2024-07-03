import subprocess


def check_java_installed():
    try:
        # Run the java -version command and capture the output
        result = subprocess.run(
            ["java", "-version"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        output = result.stderr.splitlines()[0]  # The version info is in stderr

        # Parse the Java version from the output
        if "version" in output:
            version_str: str = output.split('"')[1]
            major_version = int(version_str.split(".")[0])  # Get the major version number
            return major_version

        return None
    except FileNotFoundError:
        return None


java_version = check_java_installed()

JAVA_INSTALLED = java_version is not None and java_version >= 17
