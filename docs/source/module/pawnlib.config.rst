pawnlib.config package
======================

Submodules
----------

pawnlib.config.configure module
-------------------------------

.. code-block:: python

    from pawnlib.config import configure


.. automodule:: pawnlib.config.configure
   :members:
   :undoc-members:
   :show-inheritance:

pawnlib.config.globalconfig module
----------------------------------

.. code-block:: python

    from pawnlib.config import globalconfig


.. automodule:: pawnlib.config.globalconfig
   :members:
   :undoc-members:
   :show-inheritance:


pawnlib.config.first_run_checker module
----------------------------------

.. code-block:: python

    from pawnlib.config import first_run_checker


.. automodule:: pawnlib.config.first_run_checker
   :members:
   :undoc-members:
   :show-inheritance:


pawnlib.config.first_run_checker.one_time_run
--------------------------------------------

.. code-block:: python
    :emphasize-lines: 3, 6, 17

    from pawnlib.config import one_time_run

    if one_time_run():
        print("Just one time run")


pawnlib.config.globalconfig.pawnlib_config
--------------------------------------------

.. code-block:: python
    :emphasize-lines: 3, 6, 17

    from pawnlib.config.globalconfig import pawnlib_config

    pawnlib_config.set(param=1)

    result = pawnlib_config.get("params")
    >> 1

    print(pawnlib_config.to_dict())
    >>
       {
          PAWN_INI: False
          PAWN_VERBOSE: 0
          PAWN_TIMEOUT: 7000
          PAWN_APP_LOGGER:
          PAWN_ERROR_LOGGER:
          PAWN_VERSION: Pawnlib/0.0.2
          PAWN_GLOBAL_NAME: pawnlib_global_config_P2707BP1-0VN1HJA9-DVWMRDS2-98L6IO0U,
          params: 1
       }
