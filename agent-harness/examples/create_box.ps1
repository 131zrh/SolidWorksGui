cli-anything-solidworks --json --project demo.session.json project new demo.session.json
cli-anything-solidworks --json --project demo.session.json part box --width 0.08 --depth 0.05 --height 0.02 --save-as demo_box.SLDPRT
cli-anything-solidworks --json --project demo.session.json view isometric
cli-anything-solidworks --json --project demo.session.json preview capture --output-root .
