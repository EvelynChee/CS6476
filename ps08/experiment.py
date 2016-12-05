import os
import time

from ps8 import *


# Driver/helper code
def build_motion_history_image(builder_class, video_filename, save_frames={}, mhi_frame=None, mhi_filename=None,
                               **kwargs):
    """Instantiate and run a motion history builder on a given video, return MHI.

    Creates an object of type builder_class, passing in initial video frame,
    and any additional keyword arguments.

    Parameters
    ----------
        builder_class: motion history builder class to instantiate
        video_filename: path to input video file
        save_frames: output binary motion images to save {<frame number>: <filename>}
        mhi_frame: which frame to obtain the motion history image at
        mhi_filename: output filename to save motion history image
        kwargs: arbitrary keyword arguments passed on to constructor

    Returns
    -------
        mhi: float motion history image generated by builder, values in [0.0, 1.0]
    """

    # Open video file
    video = cv2.VideoCapture(video_filename)
    print("Video: {} ({}x{}, {:.2f} fps, {} frames)".format(
        video_filename,
        int(video.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),
        int(video.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)),
        video.get(cv2.cv.CV_CAP_PROP_FPS),
        int(video.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))))

    # Initialize objects
    mhi_builder = None
    mhi = None
    frame_num = 0

    # Loop over video (till last frame or Ctrl+C is presssed)
    while True:
        try:
            # Try to read a frame
            okay, frame = video.read()
            if not okay:
                break  # no more frames, or can't read video

            # Initialize motion history builder (one-time only)
            if mhi_builder is None:
                mhi_builder = builder_class(frame, **kwargs)

            # Process frame
            motion_image = mhi_builder.process(frame)  # TODO: implement this!

            if False:  # For debugging, it shows every frame
                out_frame = motion_image.copy()
                cv2.imshow('frame', out_frame)
                cv2.waitKey(1)  # Set to 0 if you want to continue by pressing any key

            # Save output, if indicated
            if frame_num in save_frames:
                cv2.imwrite(save_frames[frame_num], np.uint8(motion_image * 255))  # scale [0, 1] => [0, 255]

            # Grab MHI, if indicated
            if frame_num == mhi_frame:
                mhi = mhi_builder.get_MHI()
                print("MHI frame: {}".format(mhi_frame))
                break  # uncomment for early stop

            # Update frame number
            frame_num += 1
        except KeyboardInterrupt:  # press ^C to quit
            break

    # If not obtained earlier, get MHI now
    if mhi is None:
        mhi = mhi_builder.get_MHI()

    # Save MHI, if filename is given
    if mhi_filename is not None:
        cv2.imwrite(mhi_filename, np.uint8(mhi * 255))  # scale [0, 1] => [0, 255]

    return mhi


def get_cs_moment_features(n_actions, n_participants, n_trials, default_params, custom_params):
    """ Computes the central and scale features for each video.

    Parameters
    ----------
        n_actions (int): number of actions, in this problem set: 3
        n_participants (int): number of participants, in this problem set: 3
        n_trials (int): number of trials, in this problem set: 3
        default_params (dict): default values for parameters in the MHI Builder
        custom_params (dict): custom parameters for specific video files to be used in the MHI Builder

    Returns
    -------
        central_moment_features (dict): 16 features (8 MHI, 8 MEI) as one vector, key: (<action>, <participant>, <trial>)
        scaled_moment_features (dict): 16 features (8 MHI, 8 MEI) as one vector, key: (<action>, <participant>, <trial>)
    """

    central_moment_features = {}  # 16 features (8 MHI, 8 MEI) as one vector, key: (<action>, <participant>, <trial>)
    scaled_moment_features = {}  # similarly, scaled central moments

    # Loop for each action, participant, trial
    print("Computing features for each video...")
    for a in range(1, n_actions + 1):  # actions
        for p in range(1, n_participants + 1):  # participants
            for t in range(1, n_trials + 1):  # trials
                video_filename = os.path.join(input_dir, "PS8A{}P{}T{}.mp4".format(a, p, t))
                mhi = build_motion_history_image(MotionHistoryBuilder, video_filename,
                                                 **dict(default_params, **custom_params.get((a, p, t), {})))

                # cv2.imshow("MHI: PS8A{}P{}T{}.mp4".format(a, p, t), mhi)  # [debug]
                # cv2.waitKey(1)  # uncomment if using imshow

                mei = np.uint8(mhi > 0)
                mhi_moments = Moments(mhi)
                mei_moments = Moments(mei)
                central_moment_features[(a, p, t)] = np.hstack(
                    (mhi_moments.get_central_moments(), mei_moments.get_central_moments()))
                scaled_moment_features[(a, p, t)] = np.hstack(
                    (mhi_moments.get_scaled_moments(), mei_moments.get_scaled_moments()))

    return central_moment_features, scaled_moment_features


def match_features(a_features_dict, b_features_dict, n_actions, scale=1):
    """Compare features, tally matches for each action pair to produce a confusion matrix.

    Note: Skips comparison for keys that are identical in the two dicts.

    Parameters
    ----------
        a_features_dict (dict): one set of features, as a dict with key: (<action>, <participant>, <trial>)
        b_features_dict (dict): another set of features like a_features
        n_actions (int): number of distinct actions present in the feature sets
        scale (float): scale factor for compute_feature_difference (if needed)

    Returns
    -------
        confusion_matrix (numpy.array): table of matches found, n_actions by n_actions
    """

    confusion_matrix = np.zeros((n_actions, n_actions), dtype=np.float_)
    for a_key, a_features in a_features_dict.items():
        min_diff = np.inf
        best_match = None
        for b_key, b_features in b_features_dict.items():
            if a_key == b_key:
                continue  # don't compare with yourself!
            diff = compute_feature_difference(a_features, b_features)  # TODO: implement this!
            if diff < min_diff:
                min_diff = diff
                best_match = b_key
        if best_match is not None:
            # print("{} matches {}, diff: {}".format(a_key, b_key, min_diff))  # [debug]
            confusion_matrix[a_key[0] - 1, best_match[0] - 1] += 1  # note: 1-based to 0-based indexing

    confusion_matrix /= confusion_matrix.sum(axis=1)[:, np.newaxis]  # normalize confusion_matrix along each row
    return confusion_matrix


def main():
    # Note: Comment out parts of this code as necessary
    start = time.time()

    # 1a
    build_motion_history_image(MotionHistoryBuilder,  # motion history builder class
                               os.path.join(input_dir, "PS8A1P1T1.mp4"),  # input video
                               save_frames={
                                   10: os.path.join(output_dir, 'ps8-1-a-1.png'),
                                   20: os.path.join(output_dir, 'ps8-1-a-2.png'),
                                   30: os.path.join(output_dir, 'ps8-1-a-3.png')
                               },
                               theta=10,
                               tau=30)  # output motion images to save, mapped to filenames
    # TODO: Specify any other keyword args that your motion history builder expects, e.g. theta, tau

    # 1b
    build_motion_history_image(MotionHistoryBuilder,  # motion history builder class
                               os.path.join(input_dir, "PS8A1P1T1.mp4"),
                               # TODO: choose sequence (person, trial) for action A1
                               mhi_frame=90,  # TODO: pick a good frame to obtain MHI at, i.e. when action just ends
                               mhi_filename=os.path.join(output_dir, 'ps8-1-b-1.png'),
                               theta=10,
                               tau=30)
    # Specify any other keyword args that your motion history builder expects, e.g. theta, tau

    # TODO: Similarly for actions A2 & A3

    # 1b A2
    build_motion_history_image(MotionHistoryBuilder,  # motion history builder class
                               os.path.join(input_dir, "PS8A2P1T1.mp4"),
                               # TODO: choose sequence (person, trial) for action A2
                               mhi_frame=90,  # TODO: pick a good frame to obtain MHI at, i.e. when action just ends
                               mhi_filename=os.path.join(output_dir, 'ps8-1-b-2.png'),
                               theta=10,
                               tau=30)
    # Specify any other keyword args that your motion history builder expects, e.g. theta, tau

    # 1b A3
    build_motion_history_image(MotionHistoryBuilder,  # motion history builder class
                               os.path.join(input_dir, "PS8A3P1T1.mp4"),
                               # TODO: choose sequence (person, trial) for action A3
                               mhi_frame=90,  # TODO: pick a good frame to obtain MHI at, i.e. when action just ends
                               mhi_filename=os.path.join(output_dir, 'ps8-1-b-3.png'),
                               theta=10,
                               tau=30)
    # Specify any other keyword args that your motion history builder expects, e.g. theta, tau

    # 2a
    # Compute MHI and MEI features (unscaled and scaled central moments) for each video

    # Parameters for build_motion_history(), overriden by custom_params for specified videos
    default_params = dict(mhi_frame=60)  # params for build_motion_history(), overriden by custom_params for specified videos

    # Note: To specify custom parameters for a video, add to the dict below:
    #   (<action>, <participant>, <trial>): dict(<param1>=<value1>, <param2>=<value2>, ...)
    custom_params = {
        # (1, 1, 3): dict(mhi_frame=90),  # PS8A1P1T3.mp4 Reference value you may use a different one
        # (1, 2, 3): dict(mhi_frame=55)  # PS8A1P2T3.mp4 Reference value you may use a different one
        # You can add more if needed up to one for each video following the format:
        # (1, 3, 4): dict(mhi_frame=value1, theta=value2, tau=value3)
        (1, 1, 1): dict(mhi_frame=109, theta=10, tau=35),
        (1, 1, 2): dict(mhi_frame=95, theta=10, tau=35),
        (1, 1, 3): dict(mhi_frame=111, theta=10, tau=35),
        (1, 2, 1): dict(mhi_frame=72, theta=10, tau=25),
        (1, 2, 2): dict(mhi_frame=64, theta=10, tau=20),
        (1, 2, 3): dict(mhi_frame=68, theta=10, tau=20),
        (1, 3, 1): dict(mhi_frame=84, theta=25, tau=25),
        (1, 3, 2): dict(mhi_frame=80, theta=25, tau=25),
        (1, 3, 3): dict(mhi_frame=77, theta=25, tau=25),

        (2, 1, 1): dict(mhi_frame=55, theta=10, tau=45),
        (2, 1, 2): dict(mhi_frame=55, theta=10, tau=45),
        (2, 1, 3): dict(mhi_frame=65, theta=10, tau=55),
        (2, 2, 1): dict(mhi_frame=50, theta=10, tau=50),
        (2, 2, 2): dict(mhi_frame=50, theta=10, tau=50),
        (2, 2, 3): dict(mhi_frame=50, theta=10, tau=50),
        (2, 3, 1): dict(mhi_frame=50, theta=10, tau=45),
        (2, 3, 2): dict(mhi_frame=50, theta=10, tau=45),
        (2, 3, 3): dict(mhi_frame=50, theta=10, tau=45),

        (3, 1, 1): dict(mhi_frame=97, theta=10, tau=45),
        (3, 1, 2): dict(mhi_frame=90, theta=10, tau=45),
        (3, 1, 3): dict(mhi_frame=92, theta=10, tau=45),
        (3, 2, 1): dict(mhi_frame=74, theta=10, tau=45),
        (3, 2, 2): dict(mhi_frame=80, theta=10, tau=45),
        (3, 2, 3): dict(mhi_frame=79, theta=10, tau=45),
        (3, 3, 1): dict(mhi_frame=75, theta=20, tau=60),
        (3, 3, 2): dict(mhi_frame=90, theta=20, tau=60),
        (3, 3, 3): dict(mhi_frame=85, theta=20, tau=60),
    }

    n_actions = 3
    n_participants = 3
    n_trials = 3

    central_moment_features, scaled_moment_features = get_cs_moment_features(n_actions, n_participants, n_trials,
                                                                             default_params, custom_params)

    # Match features in a leave-one-out scheme (each video with all others)
    central_moments_confusion = match_features(central_moment_features, central_moment_features, n_actions)
    print("Confusion matrix (unscaled central moments):-")
    print(central_moments_confusion)

    # Similarly with scaled moments
    scaled_moments_confusion = match_features(scaled_moment_features, scaled_moment_features, n_actions)
    print("Confusion matrix (scaled central moments):-")
    print(scaled_moments_confusion)

    # 2b
    # Match features by testing one participant at a time (i.e. taking them out)
    # Note: Pick one between central_moment_features and scaled_moment_features
    features_P1 = {key: feature for key, feature in scaled_moment_features.items() if key[1] == 1}
    features_sans_P1 = {key: feature for key, feature in scaled_moment_features.items() if key[1] != 1}
    confusion_P1 = match_features(features_P1, features_sans_P1, n_actions)
    print("Confusion matrix for P1:-")
    print(confusion_P1)

    # TODO: Similarly for participants P2 & P3
    features_P2 = {key: feature for key, feature in scaled_moment_features.items() if key[1] == 2}
    features_sans_P2 = {key: feature for key, feature in scaled_moment_features.items() if key[1] != 2}
    confusion_P2 = match_features(features_P2, features_sans_P2, n_actions)
    print("Confusion matrix for P2:-")
    print(confusion_P2)

    features_P3 = {key: feature for key, feature in scaled_moment_features.items() if key[1] == 3}
    features_sans_P3 = {key: feature for key, feature in scaled_moment_features.items() if key[1] != 3}
    confusion_P3 = match_features(features_P3, features_sans_P3, n_actions)
    print("Confusion matrix for P3:-")
    print(confusion_P3)

    # TODO: Finally find the Average confusion matrix of P1, P2, and P3
    average_confusion = (confusion_P1 + confusion_P2 + confusion_P3) / 3
    print('Average confusion matrix')
    print(average_confusion)

    elapsed_time = time.time() - start
    print elapsed_time

if __name__ == "__main__":
    main()
