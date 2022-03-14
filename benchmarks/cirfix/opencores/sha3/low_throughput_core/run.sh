source /etc/profile.d/modules.sh
module load vcs/2017.12-SP2-1

cur_dir=`pwd`

cd $3

echo $1 $2
sed "s/$1/$2/g" vcs_sim_command > vcs_sim_command_buggy

cat vcs_sim_command_buggy
`cat vcs_sim_command_buggy`

rm vcs_sim_command_buggy

cp output_test_keccak_t1.txt $cur_dir/output_test_keccak_t1.txt
rm output_test_keccak_t1.txt

cd $cur_dir

