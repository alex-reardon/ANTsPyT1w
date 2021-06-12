import os
os.environ["TF_NUM_INTEROP_THREADS"] = "8"
os.environ["TF_NUM_INTRAOP_THREADS"] = "8"
os.environ["ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS"] = "8"

import antspyt1w
import antspynet
import ants

##### get example data + reference templates
fn = antspyt1w.get_data('PPMI-3803-20120814-MRI_T1-I340756', target_extension='.nii.gz' )
tfn = antspyt1w.get_data('T_template0', target_extension='.nii.gz' )
tfnw = antspyt1w.get_data('T_template0_WMP', target_extension='.nii.gz' )
tlrfn = antspyt1w.get_data('T_template0_LR', target_extension='.nii.gz' )
bfn = antspynet.get_antsxnet_data( "croppedMni152" )

##### read images and do simple bxt ops
bxtmethod = 't1combined[5]' # better for individual subjects
# bxtmethod = 't1' # good for templates
templatea = ants.image_read( tfn )
templatea = ( templatea * antspynet.brain_extraction( templatea, 't1' ) ).iMath( "Normalize" )
templateawmprior = ants.image_read( tfnw )
templatealr = ants.image_read( tlrfn )
templateb = ants.image_read( bfn )
templateb = ( templateb * antspynet.brain_extraction( templateb, 't1' ) ).iMath( "Normalize" )
img = ants.image_read( fn )
imgbxt = antspyt1w.brain_extraction( img )
img = img * imgbxt

# this is an unbiased method for identifying predictors that can be used to
# rank / sort data into clusters, some of which may be associated
# with outlierness or low-quality data
templatesmall = ants.resample_image( templateb, (91,109,91), use_voxels=True )
rbp = antspyt1w.random_basis_projection( img, templatesmall, 10 )

# assuming data is reasonable quality, we should proceed with the rest ...
mylr = antspyt1w.label_hemispheres( img, templatea, templatealr )

# optional - quick look at result
# ants.plot(img,axis=2,ncol=8,nslices=24, filename="/tmp/temp.png" )
##### intensity modifications
img = ants.iMath( img, "Normalize" )
img = ants.denoise_image( img, imgbxt, noise_model='Rician')
img = ants.n4_bias_field_correction( img ).iMath("Normalize")

##### hierarchical labeling
myparc = antspyt1w.deep_brain_parcellation( img, templateb,
    do_cortical_propagation=False, verbose=True )

##### accumulate data into data frames
hemi = antspyt1w.map_segmentation_to_dataframe( "hemisphere", myparc['hemisphere_labels'] )
tissue = antspyt1w.map_segmentation_to_dataframe( "tissues", myparc['tissue_segmentation'] )
dktl = antspyt1w.map_segmentation_to_dataframe( "lobes", myparc['dkt_lobes'] )
dktp = antspyt1w.map_segmentation_to_dataframe( "dkt", myparc['dkt_parcellation'] )

##### traditional deformable registration as a high-resolution complement to above
reg = antspyt1w.hemi_reg(
    input_image = img,
    input_image_tissue_segmentation = myparc['tissue_segmentation'],
    input_image_hemisphere_segmentation = myparc['hemisphere_labels'],
    input_template=templatea,
    input_template_hemisphere_labels=templatealr,
    output_prefix="/tmp/SYN",
    is_test=False )

##### how to use the hemi-reg output to generate any roi value from a template roi
wm_tracts = ants.image_read( antspyt1w.get_data( "wm_major_tracts", target_extension='.nii.gz' ) )
wm_tractsL = ants.apply_transforms( img, wm_tracts, reg['synL']['invtransforms'],
  interpolator='genericLabel' ) * ants.threshold_image( mylr, 1, 1  )
wm_tractsR = ants.apply_transforms( img, wm_tracts, reg['synR']['invtransforms'],
  interpolator='genericLabel' ) * ants.threshold_image( mylr, 2, 2  )
wmtdfL = antspyt1w.map_segmentation_to_dataframe( "wm_major_tracts", wm_tractsL )
wmtdfR = antspyt1w.map_segmentation_to_dataframe( "wm_major_tracts", wm_tractsR )

##### specialized labeling for hippocampus
hippLR = antspyt1w.deep_hippo( img, templateb )

##### below here are more exploratory nice to have outputs
myhypo = antspyt1w.t1_hypointensity( img,
  myparc['tissue_probabilities'][3], # wm posteriors
  templatea,
  templateawmprior )

##### specialized labeling for hypothalamus
# FIXME hypothalamus
