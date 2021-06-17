        
from tensorflow.keras import backend as K
import numpy as np
import tensorflow as tf

# Helper function to enable loss function to be flexibly used for 
# both 2D or 3D image segmentation - source: https://github.com/frankkramer-lab/MIScnn
def identify_axis(shape):
    # Three dimensional
    if len(shape) == 5 : return [1,2,3]
    # Two dimensional
    elif len(shape) == 4 : return [1,2]
    # Exception - Unknown
    else : raise ValueError('Metric: Shape of tensor is neither 2D or 3D.')


################################
#           Dice loss          #
################################
def dice_loss(delta = 0.5, smooth = 0.000001):
    """Dice loss originates from Sørensen–Dice coefficient, which is a statistic developed in 1940s to gauge the similarity between two samples.
    
    Parameters
    ----------
    delta : float, optional
        controls weight given to false positive and false negatives, by default 0.5
    smooth : float, optional
        smoothing constant to prevent division by zero errors, by default 0.000001
    """
    def loss_function(y_true, y_pred):
        axis = identify_axis(y_true.get_shape())
        # Calculate true positives (tp), false negatives (fn) and false positives (fp)
        tp = K.sum(y_true * y_pred, axis=axis)
        fn = K.sum(y_true * (1-y_pred), axis=axis)
        fp = K.sum((1-y_true) * y_pred, axis=axis)
        # Calculate Dice score
        dice_class = (tp + smooth)/(tp + delta*fn + (1-delta)*fp + smooth)
        # Sum up classes to one score
        dice_loss = K.sum(1-dice_class, axis=[-1])
        # adjusts loss to account for number of classes
        num_classes = K.cast(K.shape(y_true)[-1],'float32')
        dice_loss = dice_loss / num_classes
        return dice_loss
        
    return loss_function


################################
#         Tversky loss         #
################################
def tversky_loss(delta = 0.7, smooth = 0.000001):
    """Tversky loss function for image segmentation using 3D fully convolutional deep networks
	Link: https://arxiv.org/abs/1706.05721

    Parameters
    ----------
    delta : float, optional
        controls weight given to false positive and false negatives, by default 0.7
    smooth : float, optional
        smoothing constant to prevent division by zero errors, by default 0.000001
    """
    def loss_function(y_true, y_pred):
        axis = identify_axis(y_true.get_shape())
        # Calculate true positives (tp), false negatives (fn) and false positives (fp)   
        tp = K.sum(y_true * y_pred, axis=axis)
        fn = K.sum(y_true * (1-y_pred), axis=axis)
        fp = K.sum((1-y_true) * y_pred, axis=axis)
        tversky_class = (tp + smooth)/(tp + delta*fn + (1-delta)*fp + smooth)
        # Sum up classes to one score
        tversky_loss = K.sum(1-tversky_class, axis=[-1])
        # adjusts loss to account for number of classes
        num_classes = K.cast(K.shape(y_true)[-1],'float32')
        tversky_loss = tversky_loss / num_classes
        return tversky_loss

    return loss_function

################################
#       Dice coefficient       #
################################
def dice_coefficient(delta = 0.5, smooth = 0.000001):
    """The Dice similarity coefficient, also known as the Sørensen–Dice index or simply Dice coefficient, is a statistical tool which measures the similarity between two sets of data.

    Parameters
    ----------
    delta : float, optional
        controls weight given to false positive and false negatives, by default 0.5
    smooth : float, optional
        smoothing constant to prevent division by zero errors, by default 0.000001
    """
    def loss_function(y_true, y_pred):
        axis = identify_axis(y_true.get_shape())
        # Calculate true positives (tp), false negatives (fn) and false positives (fp)   
        tp = K.sum(y_true * y_pred, axis=axis)
        fn = K.sum(y_true * (1-y_pred), axis=axis)
        fp = K.sum((1-y_true) * y_pred, axis=axis)
        dice_class = (tp + smooth)/(tp + delta*fn + (1-delta)*fp + smooth)
        # Sum up classes to one score
        dice = K.sum(dice_class, axis=[-1])
        # adjusts loss to account for number of classes
        num_classes = K.cast(K.shape(y_true)[-1],'float32')
        dice = dice / num_classes
        return dice

    return loss_function

################################
#          Combo loss          #
################################
def combo_loss(alpha=0.5,beta=0.5):
    """Combo Loss: Handling Input and Output Imbalance in Multi-Organ Segmentation
    Link: https://arxiv.org/abs/1805.02798

    Parameters
    ----------
    alpha : float, optional
        controls weighting of dice and cross-entropy loss., by default 0.5
    beta : float, optional
        beta > 0.5 penalises false negatives more than false positives., by default 0.5
    """
    def loss_function(y_true,y_pred):
        dice = dice_coefficient()(y_true, y_pred)
        axis = identify_axis(y_true.get_shape())
        # Clip values to prevent division by zero error
        epsilon = K.epsilon()
        y_pred = K.clip(y_pred, epsilon, 1. - epsilon)
        cross_entropy = -y_true * K.log(y_pred)

        if beta is not None:
            beta_weight = np.array([beta, 1-beta])
            cross_entropy = beta_weight * cross_entropy
        # sum over classes
        cross_entropy = K.mean(K.sum(cross_entropy, axis=[-1]))
        if alpha is not None:
            combo_loss = (alpha * cross_entropy) - ((1 - alpha) * dice)
        else:
            combo_loss = cross_entropy - dice
        return combo_loss

    return loss_function

################################
#      Focal Tversky loss      #
################################
def focal_tversky_loss(delta=0.7, gamma=0.75, smooth=0.000001):
    """A Novel Focal Tversky loss function with improved Attention U-Net for lesion segmentation
    Link: https://arxiv.org/abs/1810.07842

    Parameters
    ----------
    gamma : float, optional
        focal parameter controls degree of down-weighting of easy examples, by default 0.75
    """
    def loss_function(y_true, y_pred):
        # Clip values to prevent division by zero error
        epsilon = K.epsilon()
        y_pred = K.clip(y_pred, epsilon, 1. - epsilon) 
        axis = identify_axis(y_true.get_shape())
        # Calculate true positives (tp), false negatives (fn) and false positives (fp)     
        tp = K.sum(y_true * y_pred, axis=axis)
        fn = K.sum(y_true * (1-y_pred), axis=axis)
        fp = K.sum((1-y_true) * y_pred, axis=axis)
        tversky_class = (tp + smooth)/(tp + delta*fn + (1-delta)*fp + smooth)
        # Sum up classes to one score
        focal_tversky_loss = K.sum(K.pow((1-tversky_class), gamma), axis=[-1])
    	# adjusts loss to account for number of classes
        num_classes = K.cast(K.shape(y_true)[-1],'float32')
        focal_tversky_loss = focal_tversky_loss / num_classes
        return focal_tversky_loss

    return loss_function


################################
#          Focal loss          #
################################
def focal_loss(alpha=None, beta=None, gamma_f=2.):
    """Focal loss is used to address the issue of the class imbalance problem. A modulation term applied to the Cross-Entropy loss function.

    Parameters
    ----------
    alpha : float, optional
        controls weight given to each class, by default None
    beta : float, optional
        controls relative weight of false positives and false negatives. Beta > 0.5 penalises false negatives more than false positives, by default None
    gamma_f : float, optional
        focal parameter controls degree of down-weighting of easy examples, by default 2.
    """
    def loss_function(y_true, y_pred):
        axis = identify_axis(y_true.get_shape())
        # Clip values to prevent division by zero error
        epsilon = K.epsilon()
        y_pred = K.clip(y_pred, epsilon, 1. - epsilon)
        cross_entropy = -y_true * K.log(y_pred)

        if beta is not None:
            beta_weight = np.array([beta, 1-beta])
            cross_entropy = beta_weight * cross_entropy

        if alpha is not None:
            alpha_weight = np.array(alpha, dtype=np.float32)
            focal_loss = alpha_weight * K.pow(1 - y_pred, gamma_f) * cross_entropy
        else:
            focal_loss = K.pow(1 - y_pred, gamma_f) * cross_entropy

        focal_loss = K.mean(K.sum(focal_loss, axis=[-1]))
        return focal_loss
        
    return loss_function

################################
#       Hybrid Focal loss      #
################################
def hybrid_focal_loss(weight=None, alpha=None, beta=None, gamma=0.75, gamma_f=2.):
    """Default is the linear unweighted sum of the Focal loss and Focal Tversky loss

    Parameters
    ----------
    weight : float, optional
        represents lambda parameter and controls weight given to Focal Tversky loss and Focal loss, by default None
    alpha : float, optional
        controls weight given to each class, by default None
    beta : float, optional
        controls relative weight of false positives and false negatives. Beta > 0.5 penalises  false negatives more than false positives, by default None
    gamma : float, optional
        Focal Tversky loss' focal parameter controls degree of down-weighting of easy examples, by default 0.75
    gamma_f : float, optional
        Focal loss' focal parameter controls degree of down-weighting of easy examples, by default 2.
    """
    def loss_function(y_true,y_pred):
      # Obtain Focal Dice loss
      focal_tversky = focal_tversky_loss(gamma=gamma)(y_true,y_pred)
      # Obtain Focal loss
      focal = focal_loss(alpha=alpha, beta=beta, gamma_f=gamma_f)(y_true,y_pred)
      # return weighted sum of Focal loss and Focal Dice loss
      if weight is not None:
        return (weight * focal_tversky) + ((1-weight) * focal)  
      else:
        return focal_tversky + focal

    return loss_function

################################
#     Asymmetric Focal loss    #
################################
def asymmetric_focal_loss(delta=0.25, gamma=2):
    """For Imbalanced datasets

    Parameters
    ----------
    delta : float, optional
        controls weight given to false positive and false negatives, by default 0.25
    gamma : float, optional
        Focal Tversky loss' focal parameter controls degree of down-weighting of easy examples, by default 2.0
    """
    def loss_function(y_true, y_pred):
        axis = identify_axis(y_true.get_shape())

        # convert into integer values for tf.where
        y_true_int = tf.cast(y_true, 'uint32')
        # inverts 1 to 0 and 0 to 1
        y_not_true = tf.where((y_true_int==0)|(y_true_int==1), y_true_int^1, y_true_int)

        # predictions for foreground and background class
        foreground = y_pred * y_true 
        background = y_pred * y_not_true     

        # Clip values to prevent division by zero error
        epsilon = K.epsilon()
	# Clip values to prevent division by zero error
        y_pred = K.clip(y_pred, epsilon, 1. - epsilon)
	
        axis = identify_axis(y_true.get_shape())  
	
        cross_entropy = -y_true * K.log(y_pred)
	
	# Calculate background Focal loss with background suppression
        back_ce = K.pow(1 - y_pred[:,:,:,0], gamma) * cross_entropy[:,:,:,0]
        back_ce =  (1 - delta) * back_ce

	# Calcualte foreground Focal loss component no suppresion
        fore_ce = cross_entropy[:,:,:,1]
        fore_ce = delta * fore_ce

        loss = K.mean(K.sum(tf.stack([back_ce, fore_ce],axis=-1),axis=-1))

        return loss

    return loss_function

#################################
# Asymmetric Focal Tversky loss #
#################################
def asymmetric_focal_tversky_loss(delta=0.7, gamma=0.75, smooth=0.000001):
    """This is the implementation for binary segmentation.

    Parameters
    ----------
    delta : float, optional
        controls weight given to false positive and false negatives, by default 0.7
    gamma : float, optional
        focal parameter controls degree of down-weighting of easy examples, by default 0.75
    smooth : float, optional
        smooithing constant to prevent division by 0 errors, by default 0.000001
    """
    def loss_function(y_true, y_pred):
        # Clip values to prevent division by zero error
        epsilon = K.epsilon()
        y_pred = K.clip(y_pred, epsilon, 1. - epsilon)

        axis = identify_axis(y_true.get_shape())
        # Calculate true positives (tp), false negatives (fn) and false positives (fp)     
        tp = K.sum(y_true * y_pred, axis=axis)
        fn = K.sum(y_true * (1-y_pred), axis=axis)
        fp = K.sum((1-y_true) * y_pred, axis=axis)
        dice_class = (tp + smooth)/(tp + delta*fn + (1-delta)*fp + smooth)

        #calculate losses separately for each class, only suppressing background class
        back_dice = K.pow(1-dice_class[:,0], gamma)
        fore_dice = 1-dice_class[:,1]

        # Sum up classes to one score
        loss = K.sum(tf.stack([back_dice, fore_dice],axis=-1),axis=[-1])

        # adjusts loss to account for number of classes
        num_classes = K.cast(K.shape(y_true)[-1],'float32')
        loss = loss / num_classes
        return loss

    return loss_function


################################
#      Unified Focal loss      #
################################
def unified_focal_loss(weight=0.5, delta=0.6, gamma=0.2):
    """The Unified Focal loss is a new compound loss function that unifies Dice-based and cross entropy-based loss functions into a single framework.

    Parameters
    ----------
    weight : float, optional
        represents lambda parameter and controls weight given to Asymmetric Focal Tversky loss and Asymmetric Focal loss, by default 0.5
    delta : float, optional
        controls weight given to each class, by default 0.6
    gamma : float, optional
        focal parameter controls the degree of background suppression and foreground enhancement, by default 0.2
    """
    def loss_function(y_true,y_pred):
      # Obtain Asymmetric Focal Tversky loss
      asymmetric_ftl = asymmetric_focal_tversky_loss(delta=delta, gamma=gamma)(y_true,y_pred)
      # Obtain Asymmetric Focal loss
      asymmetric_fl = asymmetric_focal_loss(delta=delta, gamma=gamma)(y_true,y_pred)
      # return weighted sum of Asymmetrical Focal loss and Asymmetric Focal Tversky loss
      if weight is not None:
        return (weight * asymmetric_ftl) + ((1-weight) * asymmetric_fl)  
      else:
        return asymmetric_ftl + asymmetric_fl

    return loss_function
