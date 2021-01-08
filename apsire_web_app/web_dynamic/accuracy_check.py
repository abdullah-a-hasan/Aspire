from aspire_aligner.aligner import test_accuracy
from aspire_aligner.helpers import file_to_list

# ref_l1 = ['apples', 'oranges', 'bananas', 'turnips']
# ref_l2 = ['تفاح', 'برتقال', 'موز', 'قرنبيط']
# alg_l1 = ['apples', 'oranges', 'bananas', 'turnips', 'tata']
# alg_l2 = ['تفاح', 'برتقال', 'موز', 'قرنبيط', 'تاتا']

algorithm = 'hualign'  # aspire bleualign hualign
s_code = 'en'
t_code = 'es'
nums = ['01', '02']

hand_aligned_path = "C:\\Users\\blazi\\Desktop\\align-tests\\hand-aligned\\{s_code}-{t_code}\\".format(s_code=s_code,
                                                                                                       t_code=t_code)

for num in nums:
    print('Pair: ', num)
    ref_l1 = file_to_list(hand_aligned_path + '{num}_{s_code}.txt'.format(num=num, s_code=s_code))
    ref_l2 = file_to_list(hand_aligned_path + '{num}_{t_code}.txt'.format(num=num, t_code=t_code))

    auto_aligned_path = "C:\\Users\\blazi\\Desktop\\align-tests\\auto-aligned\\{s_code}-{t_code}\\{algorithm}\\".format(
        s_code=s_code, t_code=t_code, algorithm=algorithm)

    alg_l1 = file_to_list(auto_aligned_path + '{num}_{s_code}.txt'.format(num=num, s_code=s_code))
    alg_l2 = file_to_list(auto_aligned_path + '{num}_{t_code}.txt'.format(num=num, t_code=t_code))

    results = test_accuracy(ref_l1, ref_l2, alg_l1, alg_l2)

    print(results)
