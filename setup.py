import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Zeugs",
    version="0.5.0",
    author="Michael Towers",
    author_email="mt.bothfeld@gmail.com",
    description="School Report Management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://bitbucket.org/gradgrind/zeugs",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
