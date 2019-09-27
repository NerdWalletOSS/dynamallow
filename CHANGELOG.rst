0.9.5 - 2019.09.26
##################

* Add support for Marshmallow version 3

0.9.4 - 2019.09.28
##################

* Bump minimum schematics version to 2.10
* Ignore schematics warnings during test

0.9.3 - 2019.04.30
##################

* Add extras_require to setup.py to specify minimum versions of schematics & marshmallow

0.9.2
#####

* Documentation update

0.9.1 - 2018.09.07
##################

https://github.com/NerdWalletOSS/dynamorm/pull/61

* **BACKWARDS INCOMPATIBLE CHANGE!**

  ``Model.query`` and ``Model.scan`` no longer return ALL available items.
  Instead they stop at each 1Mb page.  You can keep the existing behavior by
  adding a ``.recursive()`` call to the return value.

  Before::

      books = Books.scan()

  After::

      books = Books.scan().recursive()

* This version introduces the ``ReadIterator`` object which is returned from
  query and scan operations.  This object exposes functions that allow for
  better control over how a query/scan is executed.  See the usage docs for full
  details.
