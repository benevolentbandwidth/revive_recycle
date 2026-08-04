# iFixit Streamlit demo

This demo shows the Revive or Recycle iFixit repair-documentation workflow.
It uses the live public iFixit API, which does not require an API key.
Internet access is required.

## Setup

From the repository root, install the Revive service dependencies:

```bash
python -m pip install -r revive_service/requirements.txt
```

## Launch

From the repository root, run:

```bash
streamlit run revive_service/demo/ifixit_demo.py
```

The demo should open at:

```text
http://localhost:8501
```

If the browser does not open automatically, visit that URL manually.

## Suggested mentor demo

Try these inputs:

```text
iPhone 12 + cracked screen
Samsung Galaxy S22 + cracked screen
Google Pixel 7 + battery issue
```

Start with `iPhone 12` and `cracked screen`. Then enable **Include related
device variants** and run the search again to show the distinction between an
exact model match and a related model.

The custom-model input accepts common iPhone aliases. For example:

```text
iphone 17pm -> iPhone 17 Pro Max
```

The prototype also accepts common Samsung Galaxy, Google Pixel, and OnePlus
aliases, plus canonical names for tablets, laptops, and game consoles. Choose
the brand first, then choose a model from the shorter device list. Every brand
includes **Other / custom model**, and **Other / custom brand** accepts a full
brand-and-model name that is not listed.

Multiple issue types are available, including screen, battery, charging,
camera, speaker, microphone, power, liquid damage, keyboard, trackpad,
cooling, storage, joystick drift, and button repairs. Choose **Other / custom
issue** to enter a different repair problem.
