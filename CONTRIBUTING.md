To contribute, please [fork](https://guides.github.com/activities/forking/) this repository, commit your changes and then make a [pull-request](https://guides.github.com/activities/forking/#making-a-pull-request).

If you have changed Python code, please make sure, that the testsuite runs through. Install `pytest`, then execute `pytest` inside the `pmbootstrap` folder.

Additionally, the [static code analyis script](https://github.com/postmarketOS/pmbootstrap/blob/master/test/static_code_analysis.sh) must run through. Install `shellcheck` and `flake8`, then run:
```
test/static_code_analysis.sh
```

*(As of now, Travis CI can only do the static code analysis. Running the testsuite automatically is planned.)*

**If you need any help, don't hesitate to open an [issue](https://github.com/postmarketOS/pmbootstrap/issues) and ask!**
