# bszet_substitution_plan

js sucks

# Setup

The recommended way is to setup a cronjob witch executes this script every (e.g.) 15 min.

To do so you have to edit the cron job:

```
crontab -e
```

**If you wan't to execute the script as root you have to execute `sudo crontab -e`**
<br>

And add the following content at the end of the file:

```
*/15 * * * * bash -c "cd <work-dir> && python3 <path_to_script>"
```

On ubuntu you have to install the following dependencies:

```
sudo apt install python3 python3-pip
pip install -r requirements.txt
```

If you run cron as root you also should run `pip` as root.
